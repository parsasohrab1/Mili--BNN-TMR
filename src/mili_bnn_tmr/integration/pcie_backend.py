"""Linux PCIe userspace backend (mmap via /dev/mili_bnn0)."""

from __future__ import annotations

import mmap
import os
import struct
import time
from typing import BinaryIO

from mili_bnn_tmr.config import load_chip_spec
from mili_bnn_tmr.integration.backend import (
    BackendType,
    DPMTransitionResult,
    HardwareBackend,
)
from mili_bnn_tmr.integration.sim_backend import SimulatorBackend
from mili_bnn_tmr.power.dpm import PowerMode

_CSR_BASE = 0x4000_0000
_SRAM_BASE = 0x8000_0000
_BAR_CSR_OFF = 0x0
_BAR_SRAM_OFF = 0x1_0000
_BAR_SIZE = 256 * 1024

_MODE_MAP = {
    PowerMode.SLEEP: 0,
    PowerMode.IDLE: 1,
    PowerMode.NORMAL: 2,
    PowerMode.TURBO: 3,
}


class PCIeBackend(HardwareBackend):
    """Memory-mapped PCIe BAR0 access; falls back to simulator if device missing."""

    def __init__(self, device: str = "/dev/mili_bnn0") -> None:
        self._device = device
        self._fd: BinaryIO | None = None
        self._mm: mmap.mmap | None = None
        self._fallback = SimulatorBackend()
        self._power_mode = PowerMode.NORMAL
        self._open_device()

    def _open_device(self) -> None:
        if not os.path.exists(self._device):
            return
        try:
            fd = open(self._device, "r+b", buffering=0)
            mm = mmap.mmap(fd.fileno(), _BAR_SIZE, access=mmap.ACCESS_WRITE)
            self._fd = fd
            self._mm = mm
        except OSError:
            self._fd = None
            self._mm = None

    @property
    def backend_type(self) -> BackendType:
        return BackendType.PCIE if self._mm else BackendType.SIMULATOR

    def _bar_offset(self, addr: int) -> int:
        if addr >= _SRAM_BASE:
            return _BAR_SRAM_OFF + (addr - _SRAM_BASE)
        if addr >= _CSR_BASE:
            return _BAR_CSR_OFF + (addr - _CSR_BASE)
        return addr

    def read_reg(self, offset: int) -> int:
        if not self._mm:
            return self._fallback.read_reg(offset)
        off = self._bar_offset(_CSR_BASE + offset)
        return struct.unpack_from("<I", self._mm, off)[0]

    def write_reg(self, offset: int, value: int) -> None:
        if not self._mm:
            self._fallback.write_reg(offset, value)
            return
        off = self._bar_offset(_CSR_BASE + offset)
        struct.pack_into("<I", self._mm, off, value)
        self._fallback.write_reg(offset, value)  # keep state machine in sync for infer

    def dma_write(self, sram_addr: int, data: bytes) -> None:
        if not self._mm:
            self._fallback.dma_write(sram_addr, data)
            return
        off = self._bar_offset(sram_addr)
        self._mm[off : off + len(data)] = data

    def dma_read(self, sram_addr: int, length: int) -> bytes:
        if not self._mm:
            return self._fallback.dma_read(sram_addr, length)
        off = self._bar_offset(sram_addr)
        return bytes(self._mm[off : off + length])

    def set_power_mode(self, mode: PowerMode) -> DPMTransitionResult:
        if not self._mm:
            return self._fallback.set_power_mode(mode)
        return self._fallback.set_power_mode(mode)

    def start_inference(self, batch_size: int = 1) -> None:
        if not self._mm:
            self._fallback.start_inference(batch_size)
            return
        self._fallback.start_inference(batch_size)

    def wait_inference_done(self, timeout_ms: int = 10000) -> bool:
        if not self._mm:
            return self._fallback.wait_inference_done(timeout_ms)
        deadline = time.perf_counter() + timeout_ms / 1000
        while time.perf_counter() < deadline:
            if self.read_reg(0x28) & 0x02:
                return True
        return False

    def inject_tmr_fault(self, fault_lane: int = 0) -> None:
        from mili_bnn_tmr.integration.tmr_fault import inject_tmr_fault_csr

        inject_tmr_fault_csr(self, fault_lane)

    def clear_tmr_fault(self) -> None:
        from mili_bnn_tmr.integration.tmr_fault import clear_tmr_fault_csr

        clear_tmr_fault_csr(self)

    def get_tmr_stats(self) -> dict[str, int | bool]:
        if not self._mm:
            return self._fallback.get_tmr_stats()
        from mili_bnn_tmr.integration.tmr_fault import get_tmr_stats_csr

        stats = get_tmr_stats_csr(self)
        if self._fallback._last_tmr_corrected:
            stats["tmr_corrected"] = True
        return stats

    def close(self) -> None:
        if self._mm:
            self._mm.close()
        if self._fd:
            self._fd.close()
