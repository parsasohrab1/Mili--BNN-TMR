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


def test_packaging_interfaces_operating_temp():
    spec = load_chip_spec()
    assert spec.packaging == "BGA-484"
    assert "PCIe Gen4" in spec.interfaces
    assert spec.operating_temp_c == (-40, 85)
    assert spec.silicon_rev == "A0"
    assert "Linux RT" in spec.supported_os
    assert "ONNX" in spec.model_formats
