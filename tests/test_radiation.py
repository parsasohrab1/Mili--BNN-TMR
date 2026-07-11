"""Tests for Phase 5 radiation / SEU validation (FR-2)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from api.python.chip_api import MiliChip
from mili_bnn_tmr.integration.sim_backend import SimulatorBackend
from mili_bnn_tmr.radiation import (
    FaultInjector,
    FaultType,
    RadiationProfile,
    RadiationValidator,
    SEUEmulator,
    TMRMonitor,
)


@pytest.fixture
def injector():
    return FaultInjector()


@pytest.fixture
def sim_backend():
    return SimulatorBackend()


def test_lane_corrupt_always_corrected(injector):
    golden = np.array([1, 2, 3, 4], dtype=np.int32)
    for lane in range(3):
        result = injector.inject_tmr_fault(golden, fault_lane=lane)
        assert result.detected
        assert result.corrected
        np.testing.assert_array_equal(result.voted, golden)


def test_bit_flip_campaign_correction_rate(injector):
    def compute():
        return np.random.default_rng(0).integers(0, 1000, 32, dtype=np.int32)

    results = injector.run_campaign(compute, num_trials=500, seed=42)
    corrected = sum(1 for r in results if r.corrected)
    rate = 100.0 * corrected / len(results)
    assert rate >= 99.0


def test_tmr_monitor_logging(injector):
    monitor = TMRMonitor()
    golden = np.ones(8, dtype=np.int32)
    result = injector.inject_tmr_fault(golden, fault_lane=1)
    monitor.log_fault(result)
    stats = monitor.stats()
    assert stats.total_events == 1
    assert stats.correction_rate_pct == 100.0


def test_seu_emulator_mtbf_aerospace_standard():
    for profile in RadiationProfile:
        mtbf = SEUEmulator(profile).compute_mtbf()
        assert mtbf.mtbf_hours >= 10_000
        assert mtbf.meets_aerospace_standard


def test_thermal_degradation_at_85c():
    emu = SEUEmulator(RadiationProfile.COBALT_60)
    degradation = (1 - emu.thermal_derating_factor(85) / emu.thermal_derating_factor(25)) * 100
    assert degradation <= 5.0


def test_sim_backend_fault_injection(sim_backend):
    sim_backend.inject_tmr_fault(fault_lane=0)
    sim_backend.start_inference(1)
    assert sim_backend.wait_inference_done()
    stats = sim_backend.get_tmr_stats()
    assert stats["disagree"] is True
    assert stats["err_count"] >= 1
    assert stats["tmr_corrected"] is True
    sim_backend.clear_tmr_fault()


def test_radiation_validator_acceptance():
    validator = RadiationValidator(backend=SimulatorBackend())
    report = validator.validate()
    assert report.seu_correction_pct >= 99.0
    assert report.tmr_latency_overhead_pct < 5.0
    assert report.tmr_power_overhead_pct < 15.0
    assert report.thermal_degradation_85c_pct <= 5.0
    assert report.mtbf_meets_standard
    assert report.passed


def test_chip_api_radiation_validation(tmp_path):
    chip = MiliChip(use_hardware=True)
    log_path = tmp_path / "seu.json"
    report = chip.run_radiation_validation(log_path=str(log_path))
    assert report.passed
    assert log_path.exists()
    data = json.loads(log_path.read_text(encoding="utf-8"))
    assert "events" in data
    assert "stats" in data


def test_scenario_benchmarks_include_radiation():
    validator = RadiationValidator()
    scenarios = validator.run_scenario_benchmarks()
    assert "radiation_SEU" in scenarios
    assert "thermal_stress" in scenarios
    assert "high_vibration" in scenarios
    assert scenarios["radiation_SEU"]["tmr_effectiveness_pct"] >= 99.0
