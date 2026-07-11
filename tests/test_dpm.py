"""Tests for Dynamic Power Management."""

from mili_bnn_tmr.config import load_chip_spec
from mili_bnn_tmr.power import DynamicPowerManager, PowerMode


def test_initial_mode_is_normal():
    dpm = DynamicPowerManager()
    assert dpm.current_mode == PowerMode.NORMAL


def test_select_sleep_on_idle_workload():
    dpm = DynamicPowerManager()
    assert dpm.select_mode(batch_size=0, queue_depth=0) == PowerMode.SLEEP


def test_select_turbo_on_heavy_workload():
    dpm = DynamicPowerManager()
    assert dpm.select_mode(batch_size=64, queue_depth=10) == PowerMode.TURBO


def test_transition_changes_mode():
    dpm = DynamicPowerManager()
    transition = dpm.transition_to(PowerMode.IDLE)
    assert dpm.current_mode == PowerMode.IDLE
    assert transition.to_mode == PowerMode.IDLE


def test_auto_adjust_no_op_when_same_mode():
    dpm = DynamicPowerManager()
    transition = dpm.auto_adjust(batch_size=16)
    assert transition.estimated_latency_us == 0


def test_power_states_match_spec():
    spec = load_chip_spec()
    dpm = DynamicPowerManager(spec)
    for mode in PowerMode:
        dpm.transition_to(mode)
        state = dpm.current_state
        spec_state = spec.power_states[mode.value]
        assert state.frequency_mhz == spec_state.frequency_mhz
        assert state.power_w == spec_state.power_w
