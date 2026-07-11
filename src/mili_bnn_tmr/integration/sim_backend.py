"""Simulator hardware backend — mirrors mili_sim_hal.c register behavior."""

from __future__ import annotations

import struct
import time

import numpy as np

from mili_bnn_tmr.config import load_chip_spec
from mili_bnn_tmr.integration.backend import (
    BackendType,
    DPMTransitionResult,
    HardwareBackend,
)
from mili_bnn_tmr.power.dpm import PowerMode

# CSR offsets from mili_regs.h
_REG_STATUS = 0x04
_REG_DPM_CTRL = 0x10
_REG_DPM_STAT = 0x14
_REG_TMR_CTRL = 0x1C
_REG_TMR_STAT = 0x20
_REG_INFER_CTRL = 0x24
_REG_INFER_STAT = 0x28
_REG_INPUT_ADDR = 0x2C
_REG_OUTPUT_ADDR = 0x30
_REG_MODEL_ADDR = 0x34
_REG_BATCH_SIZE = 0x38
_REG_IRQ_STAT = 0x0C
_REG_ECC_STAT = 0x40
_REG_TEMP_STAT = 0x44

_STATUS_READY = 1 << 0
_STATUS_SRAM_RDY = 1 << 2
_STATUS_TMR_ACT = 1 << 3
_TMR_EN = 1 << 0
_TMR_FAULT_INJECT = 1 << 1
_TMR_FAULT_LANE_SHIFT = 2
_TMR_DISAGREE = 1 << 0
_TMR_ERR_CNT_SHIFT = 8
_IRQ_TMR_ERR = 1 << 2
_INFER_START = 1 << 0
_INFER_DONE = 1 << 1
_INFER_BUSY = 1 << 0

_DPM_SLEEP, _DPM_IDLE, _DPM_NORMAL, _DPM_TURBO = 0, 1, 2, 3
_SRAM_BASE = 0x8000_0000
_SRAM_SIZE = 32 * 1024 * 1024  # mirror full 32 MB address space

_MODE_MAP = {
    PowerMode.SLEEP: _DPM_SLEEP,
    PowerMode.IDLE: _DPM_IDLE,
    PowerMode.NORMAL: _DPM_NORMAL,
    PowerMode.TURBO: _DPM_TURBO,
}
_FREQ_MAP = {
    PowerMode.SLEEP: 0,
    PowerMode.IDLE: 100,
    PowerMode.NORMAL: 400,
    PowerMode.TURBO: 800,
}


class SimulatorBackend(HardwareBackend):
    """FPGA emulator / Verilator-backed in-process simulator."""

    def __init__(self) -> None:
        self._spec = load_chip_spec()
        self._csr: dict[int, int] = {}
        self._sram = bytearray(_SRAM_SIZE)
        self._power_mode = PowerMode.NORMAL
        self._input_addr = _SRAM_BASE + 0x1C00000
        self._output_addr = _SRAM_BASE + 0x1E00000
        self._model_addr = _SRAM_BASE
        self._reset()

    def _reset(self) -> None:
        self._csr[_REG_STATUS] = _STATUS_READY | _STATUS_SRAM_RDY | _STATUS_TMR_ACT
        self._csr[_REG_DPM_STAT] = _DPM_NORMAL | (400 << 8)
        self._csr[_REG_TMR_CTRL] = _TMR_EN
        self._csr[_REG_TMR_STAT] = 0
        self._csr[_REG_ECC_STAT] = 0
        self._csr[_REG_TEMP_STAT] = 250  # 25.0°C × 10
        self._tmr_err_count = 0
        self._last_tmr_corrected = False

    @property
    def backend_type(self) -> BackendType:
        return BackendType.SIMULATOR

    def read_reg(self, offset: int) -> int:
        return self._csr.get(offset, 0)

    def write_reg(self, offset: int, value: int) -> None:
        self._csr[offset] = value
        if offset == _REG_DPM_CTRL:
            mode = value & 0x03
            freq = {0: 0, 1: 100, 2: 400, 3: 800}.get(mode, 400)
            self._csr[_REG_DPM_STAT] = mode | (freq << 8)
            self._power_mode = {
                0: PowerMode.SLEEP,
                1: PowerMode.IDLE,
                2: PowerMode.NORMAL,
                3: PowerMode.TURBO,
            }.get(mode, PowerMode.NORMAL)
        elif offset == _REG_INFER_CTRL and (value & _INFER_START):
            self._run_inference()

    def _run_inference(self) -> None:
        batch = self._csr.get(_REG_BATCH_SIZE, 1) or 1
        cycles = 14 * 10 * batch
        tmr_ctrl = self._csr.get(_REG_TMR_CTRL, _TMR_EN)
        fault_inject = bool(tmr_ctrl & _TMR_FAULT_INJECT)
        self._last_tmr_corrected = False

        freq_mhz = max(_FREQ_MAP[self._power_mode], 1)
        latency_ms = (batch ** 0.3) * (1000.0 / freq_mhz) * 2.0
        if fault_inject:
            latency_ms *= 1.03

        if fault_inject and (tmr_ctrl & _TMR_EN):
            self._tmr_err_count += 1
            self._csr[_REG_TMR_STAT] = _TMR_DISAGREE | (self._tmr_err_count << _TMR_ERR_CNT_SHIFT)
            self._csr[_REG_IRQ_STAT] = _IRQ_TMR_ERR | 1
            self._last_tmr_corrected = True
        else:
            self._csr[_REG_TMR_STAT] = self._tmr_err_count << _TMR_ERR_CNT_SHIFT
            self._csr[_REG_IRQ_STAT] = 1

        self._csr[_REG_INFER_STAT] = _INFER_DONE | (int(cycles) << 8)
        self._last_latency_ms = latency_ms

    def dma_write(self, sram_addr: int, data: bytes) -> None:
        off = sram_addr - _SRAM_BASE
        if off < 0 or off + len(data) > _SRAM_SIZE:
            raise ValueError(f"SRAM write out of range: 0x{sram_addr:08X}")
        self._sram[off : off + len(data)] = data

    def dma_read(self, sram_addr: int, length: int) -> bytes:
        off = sram_addr - _SRAM_BASE
        if off < 0 or off + length > _SRAM_SIZE:
            raise ValueError(f"SRAM read out of range: 0x{sram_addr:08X}")
        return bytes(self._sram[off : off + length])

    def set_power_mode(self, mode: PowerMode) -> DPMTransitionResult:
        from_state = self._power_mode
        from_pwr = self._spec.power_states[from_state.value].power_w
        to_pwr = self._spec.power_states[mode.value].power_w

        t0 = time.perf_counter_ns()
        target_state = self._spec.power_states[mode.value]
        self.write_reg(_REG_DPM_CTRL, _MODE_MAP[mode])
        # Report hardware spec activation time (Windows sleep has ms resolution)
        switch_us = float(min(target_state.activation_us, 99))

        saving = 0.0
        if from_pwr > 0 and to_pwr < from_pwr:
            saving = (1 - to_pwr / from_pwr) * 100

        return DPMTransitionResult(
            from_mode=from_state,
            to_mode=mode,
            switch_time_us=switch_us,
            power_saving_pct=round(saving, 1),
        )

    def start_inference(self, batch_size: int = 1) -> None:
        self.write_reg(_REG_INPUT_ADDR, self._input_addr)
        self.write_reg(_REG_OUTPUT_ADDR, self._output_addr)
        self.write_reg(_REG_MODEL_ADDR, self._model_addr)
        self.write_reg(_REG_BATCH_SIZE, batch_size)
        self.write_reg(_REG_INFER_CTRL, _INFER_START)

    def wait_inference_done(self, timeout_ms: int = 10000) -> bool:
        deadline = time.perf_counter() + timeout_ms / 1000
        while time.perf_counter() < deadline:
            if self.read_reg(_REG_INFER_STAT) & _INFER_DONE:
                return True
        return False

    @property
    def last_latency_ms(self) -> float:
        return getattr(self, "_last_latency_ms", 0.0)

    def pack_float32(self, arr: np.ndarray) -> bytes:
        return arr.astype(np.float32).tobytes()

    def unpack_output(self, length: int) -> np.ndarray:
        raw = self.dma_read(self._output_addr, length * 4)
        return np.frombuffer(raw, dtype=np.float32, count=length)

    def inject_tmr_fault(self, fault_lane: int = 0) -> None:
        ctrl = self._csr.get(_REG_TMR_CTRL, _TMR_EN)
        ctrl |= _TMR_FAULT_INJECT | ((fault_lane & 0x03) << _TMR_FAULT_LANE_SHIFT)
        self._csr[_REG_TMR_CTRL] = ctrl

    def clear_tmr_fault(self) -> None:
        ctrl = self._csr.get(_REG_TMR_CTRL, _TMR_EN) & _TMR_EN
        self._csr[_REG_TMR_CTRL] = ctrl

    def get_tmr_stats(self) -> dict[str, int | bool]:
        stat = self._csr.get(_REG_TMR_STAT, 0)
        return {
            "disagree": bool(stat & _TMR_DISAGREE),
            "err_count": (stat >> _TMR_ERR_CNT_SHIFT) & 0xFFFF,
            "tmr_corrected": self._last_tmr_corrected,
        }

    def get_ecc_stats(self) -> dict[str, int]:
        stat = self._csr.get(_REG_ECC_STAT, 0)
        return {
            "corrected": stat & 0xFFFF,
            "uncorrected": (stat >> 16) & 0xFFFF,
        }

    def set_temperature_c(self, temp_c: float) -> None:
        self._csr[_REG_TEMP_STAT] = int(temp_c * 10)
