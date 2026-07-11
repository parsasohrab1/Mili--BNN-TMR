"""SEU event logging and TMR correction statistics."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from mili_bnn_tmr.radiation.fault_injector import FaultResult, FaultType


@dataclass
class SEUEvent:
    timestamp: float
    fault_type: str
    fault_lane: int
    detected: bool
    corrected: bool
    location: str = "tmr_voter"


@dataclass
class TMRStats:
    total_events: int = 0
    detected: int = 0
    corrected: int = 0
    undetected: int = 0
    uncorrected: int = 0
    detection_rate_pct: float = 100.0
    correction_rate_pct: float = 100.0
    err_count: int = 0


class TMRMonitor:
    """Track SEU events and TMR correction effectiveness."""

    def __init__(self) -> None:
        self._events: list[SEUEvent] = []
        self._err_count = 0

    def log_fault(self, result: FaultResult, location: str = "tmr_voter") -> SEUEvent:
        event = SEUEvent(
            timestamp=time.time(),
            fault_type=result.fault_type.value,
            fault_lane=result.fault_lane,
            detected=result.detected,
            corrected=result.corrected,
            location=location,
        )
        self._events.append(event)
        if result.detected:
            self._err_count += 1
        return event

    def log_hardware_event(
        self,
        fault_lane: int,
        detected: bool,
        corrected: bool,
        fault_type: FaultType = FaultType.LANE_CORRUPT,
        location: str = "rtl_csr",
    ) -> SEUEvent:
        event = SEUEvent(
            timestamp=time.time(),
            fault_type=fault_type.value,
            fault_lane=fault_lane,
            detected=detected,
            corrected=corrected,
            location=location,
        )
        self._events.append(event)
        if detected:
            self._err_count += 1
        return event

    @property
    def events(self) -> list[SEUEvent]:
        return list(self._events)

    def stats(self) -> TMRStats:
        total = len(self._events)
        if total == 0:
            return TMRStats()

        detected = sum(1 for e in self._events if e.detected)
        corrected = sum(1 for e in self._events if e.corrected)
        undetected = total - detected
        uncorrected = total - corrected

        return TMRStats(
            total_events=total,
            detected=detected,
            corrected=corrected,
            undetected=undetected,
            uncorrected=uncorrected,
            detection_rate_pct=round(100.0 * detected / total, 2),
            correction_rate_pct=round(100.0 * corrected / total, 2),
            err_count=self._err_count,
        )

    def export_log(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "stats": asdict(self.stats()),
            "events": [asdict(e) for e in self._events],
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def reset(self) -> None:
        self._events.clear()
        self._err_count = 0
