"""STM32H7 host bridge — serial protocol to on-board firmware."""

from __future__ import annotations

import struct
import time
from typing import IO, Any

from mili_bnn_tmr.integration.backend import (
    BackendType,
    DPMTransitionResult,
    HardwareBackend,
)
from mili_bnn_tmr.integration.sim_backend import SimulatorBackend
from mili_bnn_tmr.power.dpm import PowerMode

# Protocol: [SYNC:2 'MI'][CMD:1][LEN:4][PAYLOAD...]
_SYNC = b"MI"
_CMD_REG_RD = 0x01
_CMD_REG_WR = 0x02
_CMD_DMA_WR = 0x03
_CMD_DMA_RD = 0x04
_CMD_DPM = 0x05
_CMD_INFER = 0x06


def _open_serial_port(port: str | Any) -> IO[bytes] | None:
    if port is None:
        return None
    if hasattr(port, "read") and hasattr(port, "write"):
        return port
    try:
        import serial

        return serial.Serial(port, baudrate=115200, timeout=2.0)
    except Exception:
        return None


class STM32Backend(HardwareBackend):
    """
    Bridge to STM32H7 firmware over USB-UART (pyserial).
    Falls back to in-process simulator when no device connected.
    """

    def __init__(self, port: str | IO[bytes] | None = None) -> None:
        self._port = _open_serial_port(port)
        self._fallback = SimulatorBackend()
        self._power_mode = PowerMode.NORMAL

    @property
    def backend_type(self) -> BackendType:
        return BackendType.STM32 if self._port else BackendType.SIMULATOR

    def _xfer(self, cmd: int, payload: bytes = b"") -> bytes:
        if not self._port:
            return b""
        frame = _SYNC + struct.pack("<BI", cmd, len(payload)) + payload
        self._port.write(frame)
        hdr = self._read_exact(7)
        if hdr[:2] != _SYNC:
            raise IOError("STM32 bridge sync error")
        _, rlen = struct.unpack("<BI", hdr[2:7])
        return self._read_exact(rlen) if rlen else b""

    def _read_exact(self, n: int) -> bytes:
        if not self._port:
            return b""
        buf = b""
        while len(buf) < n:
            chunk = self._port.read(n - len(buf))
            if not chunk:
                raise IOError("STM32 bridge timeout")
            buf += chunk
        return buf

    def read_reg(self, offset: int) -> int:
        if not self._port:
            return self._fallback.read_reg(offset)
        resp = self._xfer(_CMD_REG_RD, struct.pack("<I", offset))
        return struct.unpack("<I", resp)[0]

    def write_reg(self, offset: int, value: int) -> None:
        if not self._port:
            self._fallback.write_reg(offset, value)
            return
        self._xfer(_CMD_REG_WR, struct.pack("<II", offset, value))

    def dma_write(self, sram_addr: int, data: bytes) -> None:
        if not self._port:
            self._fallback.dma_write(sram_addr, data)
            return
        self._xfer(_CMD_DMA_WR, struct.pack("<II", sram_addr, len(data)) + data)

    def dma_read(self, sram_addr: int, length: int) -> bytes:
        if not self._port:
            return self._fallback.dma_read(sram_addr, length)
        return self._xfer(_CMD_DMA_RD, struct.pack("<II", sram_addr, length))

    def set_power_mode(self, mode: PowerMode) -> DPMTransitionResult:
        if not self._port:
            return self._fallback.set_power_mode(mode)
        t0 = time.perf_counter_ns()
        resp = self._xfer(_CMD_DPM, struct.pack("<B", _MODE_TO_BYTE[mode]))
        switch_us = (time.perf_counter_ns() - t0) / 1000.0
        from_m, to_m, saving = struct.unpack("<BBf", resp[:6])
        self._power_mode = mode
        return DPMTransitionResult(
            from_mode=PowerMode(list(_MODE_TO_BYTE.keys())[from_m]),
            to_mode=mode,
            switch_time_us=switch_us,
            power_saving_pct=saving,
        )

    def start_inference(self, batch_size: int = 1) -> None:
        if not self._port:
            self._fallback.start_inference(batch_size)
            return
        self._xfer(_CMD_INFER, struct.pack("<I", batch_size))

    def wait_inference_done(self, timeout_ms: int = 10000) -> bool:
        if not self._port:
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
        if not self._port:
            return self._fallback.get_tmr_stats()
        from mili_bnn_tmr.integration.tmr_fault import get_tmr_stats_csr

        stats = get_tmr_stats_csr(self)
        if self._fallback._last_tmr_corrected:
            stats["tmr_corrected"] = True
        return stats


_MODE_TO_BYTE = {
    PowerMode.SLEEP: 0,
    PowerMode.IDLE: 1,
    PowerMode.NORMAL: 2,
    PowerMode.TURBO: 3,
}
