"""Tests for hardware gap fixes #7–#12 (RTL, CI, SRAM, FPGA, ES, BGA)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

from mili_bnn_tmr.tapeout import EngineeringSampleLot

ROOT = Path(__file__).resolve().parents[1]


def test_pcie_rtl_modules_exist():
    rtl = ROOT / "rtl"
    for name in ("pcie_pkg.sv", "pcie_phy_gen4.sv", "pcie_tlp.sv", "pcie_if.sv"):
        text = (rtl / name).read_text(encoding="utf-8")
        assert "module " in text or "package " in text


def test_pcie_if_has_gen4_stack():
    src = (ROOT / "rtl" / "pcie_if.sv").read_text(encoding="utf-8")
    assert "pcie_phy_gen4" in src
    assert "pcie_tlp" in src
    assert "SIM_DIRECT" in src


def test_sram_macro_wrapper():
    src = (ROOT / "rtl" / "sram_macro.sv").read_text(encoding="utf-8")
    assert "READ_LATENCY" in src
    assert "MILI_USE_SRAM_MACRO" in src
    bank = (ROOT / "rtl" / "sram_bank.sv").read_text(encoding="utf-8")
    assert "sram_macro" in bank


def test_verilator_signoff_gate_script():
    script = ROOT / "sim" / "verilator" / "signoff_gate.sh"
    assert script.exists()
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "continue-on-error" not in ci
    assert "signoff_gate.sh" in ci
    makefile = (ROOT / "sim" / "verilator" / "Makefile").read_text(encoding="utf-8")
    assert "top:" in makefile


def test_fpga_artix7_flow():
    fpga = ROOT / "fpga"
    assert (fpga / "Makefile").exists()
    assert (fpga / "vivado_synth.tcl").exists()
    assert (fpga / "constraints" / "artix7_dev.xdc").exists()
    board = yaml.safe_load((ROOT / "integration" / "board" / "dev_board.yaml").read_text())
    assert board["fpga"]["part"].upper().startswith("XC7A200T")


def test_engineering_sample_traceability():
    lot = EngineeringSampleLot.from_spec()
    assert 10 <= lot.quantity <= 50
    assert lot.foundry_lot
    assert lot.assembly_site
    s = lot.samples[0]
    assert s.tracking_id.startswith("TRK-")
    assert s.package_lot.startswith("BGA484-")


def test_engineering_sample_from_manifest():
    manifest = ROOT / "tapeout" / "samples" / "engineering_lot_manifest.json"
    lot = EngineeringSampleLot.from_manifest(manifest)
    assert lot.lot_id == "MILI-ES-A0-001"
    assert lot.samples[0].ate_passed is True


def test_bga484_complete_ball_map():
    pinout = ROOT / "tapeout" / "packaging" / "bga484_pinout.yaml"
    land = ROOT / "tapeout" / "packaging" / "bga484_land_pattern.csv"
    assert pinout.exists()
    assert land.exists()
    data = yaml.safe_load(pinout.read_text(encoding="utf-8"))
    assert data["package"]["ball_count"] == 484
    assert len(data["balls"]) == 484
    with land.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 484
    assert all("x_mm" in r and "y_mm" in r for r in rows)
