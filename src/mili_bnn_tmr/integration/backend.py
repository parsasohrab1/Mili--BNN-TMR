"""Hardware backend abstraction for STM32H7 / simulator / PCIe."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

import numpy as np

from mili_bnn_tmr.power.dpm import PowerMode


class BackendType(Enum):
    SIMULATOR = "simulator"
    STM32 = "stm32"
    PCIE = "pcie"


@dataclass
class DPMTransitionResult:
    from_mode: PowerMode
    to_mode: PowerMode
    switch_time_us: float
    power_saving_pct: float


@dataclass
class HardwareInferResult:
    output: np.ndarray
    latency_ms: float
    energy_mj: float
    power_mode: PowerMode
    tmr_corrected: bool


class HardwareBackend(ABC):
    """Low-level hardware access for the BNN accelerator."""

    @abstractmethod
    def read_reg(self, offset: int) -> int: ...

    @abstractmethod
    def write_reg(self, offset: int, value: int) -> None: ...

    @abstractmethod
    def dma_write(self, sram_addr: int, data: bytes) -> None: ...

    @abstractmethod
    def dma_read(self, sram_addr: int, length: int) -> bytes: ...

    @abstractmethod
    def set_power_mode(self, mode: PowerMode) -> DPMTransitionResult: ...

    @abstractmethod
    def start_inference(self, batch_size: int = 1) -> None: ...

    @abstractmethod
    def wait_inference_done(self, timeout_ms: int = 10000) -> bool: ...

    @property
    @abstractmethod
    def backend_type(self) -> BackendType: ...
