"""Software fault injection mirroring RTL TMR_CTRL fault_inject behavior."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

import numpy as np

from mili_bnn_tmr.tmr.voter import detect_disagreement, majority_vote


class FaultType(Enum):
    BIT_FLIP = "bit_flip"
    LANE_CORRUPT = "lane_corrupt"
    SRAM_ECC = "sram_ecc"


@dataclass
class FaultResult:
    golden: np.ndarray
    lane0: np.ndarray
    lane1: np.ndarray
    lane2: np.ndarray
    voted: np.ndarray
    detected: bool
    corrected: bool
    fault_lane: int
    fault_type: FaultType


class FaultInjector:
    """Inject single-event upsets into TMR lanes (RTL-compatible semantics)."""

    def inject_bit_flip(self, data: np.ndarray, bit_index: int | None = None) -> np.ndarray:
        copied = np.array(data, copy=True)
        if bit_index is None:
            bit_index = int(np.random.randint(0, copied.nbytes * 8))
        raw = bytearray(copied.tobytes())
        byte_idx = bit_index // 8
        bit_pos = bit_index % 8
        if byte_idx < len(raw):
            raw[byte_idx] ^= 1 << bit_pos
        return np.frombuffer(bytes(raw), dtype=copied.dtype).reshape(copied.shape).copy()

    def corrupt_lane(self, value: np.ndarray, lane: int) -> np.ndarray:
        """Bit-invert one lane output (matches tmr_triplex.sv fault_inject)."""
        if np.issubdtype(value.dtype, np.floating):
            bits = value.view(np.uint32)
            return (~bits).view(value.dtype)
        if np.issubdtype(value.dtype, np.integer):
            return ~value
        return ~value.astype(np.uint8)

    def inject_tmr_fault(
        self,
        golden: np.ndarray,
        fault_lane: int = 0,
        fault_type: FaultType = FaultType.LANE_CORRUPT,
    ) -> FaultResult:
        lane0 = golden.copy()
        lane1 = golden.copy()
        lane2 = golden.copy()

        if fault_type == FaultType.LANE_CORRUPT:
            lanes = [lane0, lane1, lane2]
            lanes[fault_lane % 3] = self.corrupt_lane(golden, fault_lane)
            lane0, lane1, lane2 = lanes
        elif fault_type == FaultType.BIT_FLIP:
            lanes = [lane0, lane1, lane2]
            lanes[fault_lane % 3] = self.inject_bit_flip(golden)
            lane0, lane1, lane2 = lanes
        else:
            lane0 = self.inject_bit_flip(lane0)

        voted = majority_vote(lane0, lane1, lane2)
        detected = detect_disagreement(lane0, lane1, lane2)
        corrected = np.array_equal(voted, golden)

        return FaultResult(
            golden=golden,
            lane0=lane0,
            lane1=lane1,
            lane2=lane2,
            voted=voted,
            detected=detected,
            corrected=corrected,
            fault_lane=fault_lane % 3,
            fault_type=fault_type,
        )

    def run_campaign(
        self,
        compute_fn: Callable[[], np.ndarray],
        num_trials: int = 1000,
        seed: int = 42,
    ) -> list[FaultResult]:
        rng = np.random.default_rng(seed)
        results: list[FaultResult] = []
        for _ in range(num_trials):
            golden = compute_fn()
            lane = int(rng.integers(0, 3))
            fault_type = FaultType.LANE_CORRUPT if rng.random() > 0.2 else FaultType.BIT_FLIP
            results.append(self.inject_tmr_fault(golden, fault_lane=lane, fault_type=fault_type))
        return results
