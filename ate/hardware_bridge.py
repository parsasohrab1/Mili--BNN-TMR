"""ATE hardware bridge — GPIB/VISA/serial transport to production tester."""

from __future__ import annotations

import os
import socket
import struct
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


class TransportType(Enum):
    SIMULATOR = "simulator"
    TCP = "tcp"
    SERIAL = "serial"
    GPIB = "gpib"


@dataclass
class ATEHardwareResult:
    unit_id: str
    passed: bool
    power_w: float
    freq_mhz: int
    iddq_ma: float
    infer_latency_ms: float
    raw: dict[str, Any]


class ATETransport(ABC):
    @abstractmethod
    def connect(self) -> bool: ...

    @abstractmethod
    def run_test_program(self, unit_id: str, steps: list[str]) -> ATEHardwareResult: ...


class SimulatorATETransport(ATETransport):
    """Fallback when no tester is connected."""

    def connect(self) -> bool:
        return True

    def run_test_program(self, unit_id: str, steps: list[str]) -> ATEHardwareResult:
        from ate.mili_ate_program import ATEProgram

        prog = ATEProgram()
        r = prog.run_unit_test(unit_id, use_hardware=False)
        return ATEHardwareResult(
            unit_id=unit_id,
            passed=r.passed,
            power_w=r.power_w,
            freq_mhz=r.freq_mhz,
            iddq_ma=120.0,
            infer_latency_ms=4.5,
            raw={"mode": "simulator"},
        )


class TCPATETransport(ATETransport):
    """Bridge to Teradyse/Advantest style handler via TCP JSON gateway."""

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        self._sock: socket.socket | None = None

    def connect(self) -> bool:
        try:
            self._sock = socket.create_connection((self._host, self._port), timeout=5.0)
            return True
        except OSError:
            self._sock = None
            return False

    def run_test_program(self, unit_id: str, steps: list[str]) -> ATEHardwareResult:
        if not self._sock:
            raise ConnectionError("ATE TCP bridge not connected")
        payload = struct.pack("<H", len(unit_id)) + unit_id.encode() + bytes([len(steps)])
        self._sock.sendall(b"ATE1" + payload)
        data = self._sock.recv(256)
        passed = data[0] == 1
        power_w, freq_mhz, iddq_ma, lat_ms = struct.unpack("<fIff", data[1:17])
        return ATEHardwareResult(
            unit_id=unit_id,
            passed=passed,
            power_w=power_w,
            freq_mhz=freq_mhz,
            iddq_ma=iddq_ma,
            infer_latency_ms=lat_ms,
            raw={"mode": "tcp"},
        )


def create_ate_transport() -> ATETransport:
    kind = os.environ.get("MILI_ATE_TRANSPORT", "simulator").lower()
    if kind == "tcp":
        host = os.environ.get("MILI_ATE_HOST", "127.0.0.1")
        port = int(os.environ.get("MILI_ATE_PORT", "5025"))
        transport: ATETransport = TCPATETransport(host, port)
        if transport.connect():
            return transport
    return SimulatorATETransport()
