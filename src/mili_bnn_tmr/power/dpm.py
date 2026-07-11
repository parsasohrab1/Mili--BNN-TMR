"""Dynamic Power Management (DPM) for the accelerator chip."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from mili_bnn_tmr.config import ChipSpec, PowerState, load_chip_spec


class PowerMode(Enum):
    SLEEP = "sleep"
    IDLE = "idle"
    NORMAL = "normal"
    TURBO = "turbo"


@dataclass
class PowerTransition:
    from_mode: PowerMode
    to_mode: PowerMode
    estimated_latency_us: int
    power_saving_pct: float


class DynamicPowerManager:
    """Manages chip power states based on workload."""

    def __init__(self, spec: ChipSpec | None = None):
        self._spec = spec or load_chip_spec()
        self._current = PowerMode.NORMAL

    @property
    def current_mode(self) -> PowerMode:
        return self._current

    @property
    def current_state(self) -> PowerState:
        return self._spec.power_states[self._current.value]

    def select_mode(self, batch_size: int, queue_depth: int = 0) -> PowerMode:
        """Select optimal power mode based on workload characteristics."""
        if batch_size == 0 and queue_depth == 0:
            return PowerMode.SLEEP
        if batch_size <= 4 and queue_depth < 2:
            return PowerMode.IDLE
        if batch_size >= 32 or queue_depth >= 8:
            return PowerMode.TURBO
        return PowerMode.NORMAL

    def transition_to(self, mode: PowerMode) -> PowerTransition:
        """Transition to a new power mode and return transition metadata."""
        from_state = self._spec.power_states[self._current.value]
        to_state = self._spec.power_states[mode.value]

        latency = max(from_state.activation_us, to_state.activation_us)
        saving = 0.0
        if to_state.power_w < from_state.power_w and from_state.power_w > 0:
            saving = (1 - to_state.power_w / from_state.power_w) * 100

        transition = PowerTransition(
            from_mode=self._current,
            to_mode=mode,
            estimated_latency_us=latency,
            power_saving_pct=round(saving, 1),
        )
        self._current = mode
        return transition

    def auto_adjust(self, batch_size: int, queue_depth: int = 0) -> PowerTransition:
        """Automatically select and transition to the optimal power mode."""
        target = self.select_mode(batch_size, queue_depth)
        if target == self._current:
            return PowerTransition(
                from_mode=self._current,
                to_mode=self._current,
                estimated_latency_us=0,
                power_saving_pct=0.0,
            )
        return self.transition_to(target)
