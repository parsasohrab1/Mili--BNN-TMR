"""FPGA / ASIC engineering-sample backend (DPI or register bridge)."""

from __future__ import annotations

import os
import socket
import struct
from typing import Any

from mili_bnn_tmr.integration.backend import BackendType
from mili_bnn_tmr.integration.sim_backend import SimulatorBackend


class FPGABackend(SimulatorBackend):
    """
    Talks to FPGA emulator or ASIC ES via optional DPI TCP bridge.

    Set MILI_FPGA_HOST / MILI_FPGA_PORT or pass host/port explicitly.
  Falls back to in-process register model when bridge is unavailable.
    """

    def __init__(self, host: str | None = None, port: int | None = None) -> None:
        super().__init__()
        self._host = host or os.environ.get("MILI_FPGA_HOST", "")
        self._port = port or int(os.environ.get("MILI_FPGA_PORT", "0"))
        self._sock: socket.socket | None = None
        self._remote = False
        if self._host and self._port:
            self._connect_bridge()

    def _connect_bridge(self) -> None:
        try:
            sock = socket.create_connection((self._host, self._port), timeout=2.0)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self._sock = sock
            self._remote = True
        except OSError:
            self._sock = None
            self._remote = False

    @property
    def backend_type(self) -> BackendType:
        return BackendType.FPGA

    @property
    def is_remote(self) -> bool:
        return self._remote

    def _rpc(self, op: int, offset: int, value: int = 0, payload: bytes = b"") -> Any:
        if not self._sock:
            return None
        hdr = struct.pack("<BII", op, offset, value)
        self._sock.sendall(hdr + payload)
        resp = self._sock.recv(4096)
        if not resp:
            raise ConnectionError("FPGA bridge disconnected")
        if op == 0:  # read reg
            return struct.unpack("<I", resp[:4])[0]
        return resp

    def read_reg(self, offset: int) -> int:
        if self._remote:
            val = self._rpc(0, offset)
            return int(val) if val is not None else 0
        return super().read_reg(offset)

    def write_reg(self, offset: int, value: int) -> None:
        if self._remote:
            self._rpc(1, offset, value)
            return
        super().write_reg(offset, value)

    def dma_write(self, sram_addr: int, data: bytes) -> None:
        if self._remote:
            self._rpc(2, sram_addr, len(data), data)
            return
        super().dma_write(sram_addr, data)

    def dma_read(self, sram_addr: int, length: int) -> bytes:
        if self._remote:
            resp = self._rpc(3, sram_addr, length)
            return bytes(resp) if resp else b""
        return super().dma_read(sram_addr, length)

    def inject_tmr_fault(self, fault_lane: int = 0) -> None:
        from mili_bnn_tmr.integration.tmr_fault import inject_tmr_fault_csr

        inject_tmr_fault_csr(self, fault_lane)

    def clear_tmr_fault(self) -> None:
        from mili_bnn_tmr.integration.tmr_fault import clear_tmr_fault_csr

        clear_tmr_fault_csr(self)
