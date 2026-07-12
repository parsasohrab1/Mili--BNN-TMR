"""Tests for hardware gaps #7-#12 (RTL, CI, SRAM, FPGA, ES, BGA)."""

from __future__ import annotations

import json
from pathlib import Path

from mili_bnn_tmr.tapeout import EngineeringSampleLot, SignoffRunner


ROOT = Path(__file__).resolve().parents[1]


def test_pcie_rtl_modules_exist():
    rtl = ROOT / "rtl"
    for name in ("pcie_pkg.sv", "pcie_phy_gen4.sv", "pcie_tlp.sv", "pcie_if.sv"):
        text = (rtl / name).read_text(encoding="utf-8")
        assert "module" in text or "package" in text
    pcie_if = (rtl / "pcie_if.sv").read_text(encoding="utf-8")
    assert "pcie_phy_gen4" in pcie_if
    assert "pcie_tlp" in pcie_if
    assert "SIM_DIRECT" in pcie_if


def test_sram_macro_wrapper():
    text = (ROOT / "rtl" / "sram_macro.sv").read_text(encoding="utf-8")
    assert "MILI_USE_SRAM_MACRO" in text
    assert "READ_LATENCY" in text
    bank = (ROOT / "rtl" / "sram_bank.sv").read_text(encoding="utf-8")
    assert "sram_macro" in bank


def test_ci_rtl_signoff_gate_required():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    gate = (ROOT / "sim" / "verilator" / "signoff_gate.sh").read_text(encoding="utf-8")
    assert "continue-on-error" not in ci
    assert "signoff_gate" in ci
    assert "top" in gate


def test_fpga_artix7_flow():
    fpga = ROOT / "fpga"
    assert (fpga / "Makefile").exists()
    assert (fpga / "vivado_synth.tcl").exists()
    assert (fpga / "constraints" / "artix7_dev.xdc").exists()
    dev = (ROOT / "integration" / "board" / "dev_board.yaml").read_text(encoding="utf-8")
    assert "XC7A200T" in dev
    assert "fpga/" in dev


def test_engineering_samples_traceability():
    lot = EngineeringSampleLot.from_spec()
    assert 10 <= lot.quantity <= 50
    assert lot.foundry_lot
    assert lot.assembly_site
    s = lot.samples[0]
    assert s.tracking_id.startswith("TRK-")
    assert s.package_lot


def test_engineering_samples_csv_export(tmp_path):
    lot = EngineeringSampleLot.from_spec()
    path = tmp_path / "es.csv"
    lot.export_csv(path)
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == lot.quantity + 1
    assert "tracking_id" in lines[0]


def test_bga484_complete_ball_map():
    pinout = ROOT / "tapeout" / "packaging" / "bga484_pinout.yaml"
    assert pinout.exists()
    text = pinout.read_text(encoding="utf-8")
    assert "balls:" in text
    ball_lines = [ln for ln in text.splitlines() if ln.strip().startswith(("A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "M", "N", "P", "R", "T", "U", "V", "W", "Y"))]
    assert len(ball_lines) >= 484


def test_bga484_land_pattern():
    land = ROOT / "tapeout" / "packaging" / "bga484_land_pattern.csv"
    assert land.exists()
    lines = land.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 485  # header + 484 balls


def test_signoff_gate_passes():
    report = SignoffRunner().run_signoff()
    assert report.passed
