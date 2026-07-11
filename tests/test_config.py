"""Tests for chip configuration loader."""

from mili_bnn_tmr.config import load_chip_spec


def test_load_chip_spec():
    spec = load_chip_spec()
    assert spec.technology_nm == 14
    assert spec.pe_count == 64
    assert spec.max_power_w == 50


def test_power_states_loaded():
    spec = load_chip_spec()
    assert "sleep" in spec.power_states
    assert "turbo" in spec.power_states
    assert spec.power_states["turbo"].frequency_mhz == 800


def test_requirements_loaded():
    spec = load_chip_spec()
    assert spec.requirements["max_latency_ms"] == 10
    assert spec.requirements["min_accuracy_pct"] == 95
