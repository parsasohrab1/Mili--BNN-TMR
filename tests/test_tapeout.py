"""Tests for Phase 6 tape-out and silicon bring-up."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mili_bnn_tmr.config import load_chip_spec
from mili_bnn_tmr.tapeout import (
    EngineeringSampleLot,
    SignoffRunner,
    SiliconCharacterization,
    TapeoutValidator,
)


def test_chip_spec_has_tapeout_section():
    spec = load_chip_spec()
    assert spec.tapeout
    assert spec.tapeout["foundry"] == "TSMC 14nm FinFET"
    assert spec.tapeout["packaging"] == "BGA-484"


def test_signoff_passes():
    report = SignoffRunner().run_signoff()
    assert report.drc_passed
    assert report.lvs_passed
    assert report.timing_closed
    assert report.passed


def test_silicon_characterization_meets_spec():
    char = SiliconCharacterization.from_spec()
    assert char.typical_power_w <= 30
    assert char.max_power_w < 50
    assert char.frequency_min_mhz == 400
    assert char.frequency_max_mhz == 800
    assert char.tops_per_watt >= 2.0


def test_engineering_sample_lot():
    lot = EngineeringSampleLot.from_spec()
    assert 10 <= lot.quantity <= 50
    assert lot.yield_pct > 70
    assert lot.pass_count > 0


def test_engineering_sample_export(tmp_path):
    lot = EngineeringSampleLot.from_spec()
    path = tmp_path / "samples.json"
    lot.export(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["quantity"] == lot.quantity
    assert len(data["samples"]) == lot.quantity


def test_tapeout_acceptance():
    report = TapeoutValidator().validate()
    assert report.signoff_passed
    assert report.typical_power_w <= 30
    assert report.max_power_w < 50
    assert report.yield_pct > 70
    assert report.tops_per_watt >= 2.0
    assert report.passed


def test_ate_program():
    sys_path = Path(__file__).resolve().parents[1]
    import sys
    sys.path.insert(0, str(sys_path))
    from ate.mili_ate_program import ATEProgram, TestPhase

    ate = ATEProgram()
    assert len(ate.steps) >= 6
    result = ate.run_unit_test("ES-A0-001")
    assert result.power_w <= 30
    assert 400 <= result.freq_mhz <= 800


def test_bga484_pinout_exists():
    path = Path(__file__).resolve().parents[1] / "tapeout" / "packaging" / "bga484_pinout.yaml"
    assert path.exists()
    import yaml
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["package"]["name"] == "BGA-484"
    assert data["package"]["ball_count"] == 484
    assert len(data.get("balls", {})) == 484


def test_timing_report_exists():
    path = Path(__file__).resolve().parents[1] / "tapeout" / "signoff" / "timing_report.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["timing_closed"] is True
    assert data["setup_wns_ns"] >= 0
