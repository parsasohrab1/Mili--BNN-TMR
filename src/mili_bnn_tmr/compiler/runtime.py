"""CPU runtime executor for compiled .mili models."""

from __future__ import annotations

import numpy as np

from mili_bnn_tmr.compiler.mili_format import MiliModel
from mili_bnn_tmr.compiler.quantizer import forward_bnn


class MiliRuntime:
    """Execute a .mili model (simulates on-chip inference)."""

    def __init__(self, model: MiliModel):
        self.model = model
        self._cycle_count = 0

    @property
    def input_shape(self) -> tuple[int, ...]:
        return self.model.input_shape

    @property
    def output_shape(self) -> tuple[int, ...]:
        return self.model.output_shape

    def _preprocess(self, x: np.ndarray) -> np.ndarray:
        shape = self.model.input_shape
        if x.ndim == 1 and len(shape) == 3:
            c, h, w = shape
            if x.size == h * w:
                return x.reshape(1, 1, h, w)
            if x.size == c * h * w:
                return x.reshape(1, c, h, w)
        if x.ndim == 2 and len(shape) == 3:
            _, h, w = shape
            if x.shape == (h, w):
                return x.reshape(1, 1, h, w)
        if x.ndim == 3:
            return x.reshape(1, *x.shape)
        return x

    def execute(self, input_data: np.ndarray) -> np.ndarray:
        """Run inference using the compiled BNN network."""
        x = self._preprocess(input_data.astype(np.float32))
        n_instr = max(len(self.model.instructions), len(self.model.network.layers))
        self._cycle_count = n_instr * 14
        return forward_bnn(self.model.network, x)

    @property
    def cycle_count(self) -> int:
        return self._cycle_count

    def estimate_latency_ms(self, frequency_mhz: int = 400) -> float:
        freq = max(frequency_mhz, 1)
        total = max(self._cycle_count, 14)
        return round(total / freq / 1000, 3)
