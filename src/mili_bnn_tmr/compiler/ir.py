"""Intermediate representation for the Mili BNN compiler."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

import numpy as np

MAX_LAYERS = 20
MIN_INPUT_SIZE = 32
MAX_INPUT_SIZE = 224


class LayerType(IntEnum):
    CONV = 1
    FC = 2
    MAXPOOL = 3
    BATCHNORM = 4
    RELU = 5
    FLATTEN = 6


@dataclass
class LayerIR:
    """Single layer in the network intermediate representation."""

    name: str
    op_type: LayerType
    inputs: list[str]
    outputs: list[str]
    attrs: dict[str, Any] = field(default_factory=dict)
    weights: dict[str, np.ndarray] = field(default_factory=dict)


@dataclass
class NetworkIR:
    """Full network graph before optimization."""

    name: str
    input_shape: tuple[int, ...]  # (C, H, W) or (H, W, C) normalized to (C,H,W)
    output_shape: tuple[int, ...]
    layers: list[LayerIR] = field(default_factory=list)

    def validate(self) -> None:
        if len(self.layers) > MAX_LAYERS:
            raise ValueError(f"Network exceeds {MAX_LAYERS} layer limit ({len(self.layers)})")
        _, h, w = self._spatial()
        if h < MIN_INPUT_SIZE and w < MIN_INPUT_SIZE:
            pass  # MNIST 28x28 allowed
        if max(h, w) > MAX_INPUT_SIZE:
            raise ValueError(f"Input spatial size {h}x{w} exceeds {MAX_INPUT_SIZE}")

    def _spatial(self) -> tuple[int, int, int]:
        if len(self.input_shape) == 3:
            return self.input_shape
        if len(self.input_shape) == 1:
            side = int(np.sqrt(self.input_shape[0]))
            return 1, side, side
        raise ValueError(f"Unsupported input shape: {self.input_shape}")
