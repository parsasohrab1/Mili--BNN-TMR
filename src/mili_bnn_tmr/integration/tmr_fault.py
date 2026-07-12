"""CSR-based TMR fault injection (mirrors RTL TMR_CTRL / mili_regs.h)."""

from __future__ import annotations

from mili_bnn_tmr.integration.hw_regs import read_tmr_stats

_REG_TMR_CTRL = 0x1C
_TMR_EN = 1 << 0
_TMR_FAULT_INJECT = 1 << 1
_TMR_FAULT_LANE_SHIFT = 2


def inject_tmr_fault_csr(backend, fault_lane: int = 0) -> None:
    """Write TMR_CTRL fault_inject + fault_lane on any register backend."""
    ctrl = backend.read_reg(_REG_TMR_CTRL)
    ctrl |= _TMR_EN | _TMR_FAULT_INJECT
    ctrl = (ctrl & ~(0x3 << _TMR_FAULT_LANE_SHIFT)) | ((fault_lane & 0x3) << _TMR_FAULT_LANE_SHIFT)
    backend.write_reg(_REG_TMR_CTRL, ctrl)


def clear_tmr_fault_csr(backend) -> None:
    """Clear fault_inject bit, keep TMR enabled."""
    ctrl = backend.read_reg(_REG_TMR_CTRL) & _TMR_EN
    backend.write_reg(_REG_TMR_CTRL, ctrl)


def get_tmr_stats_csr(backend) -> dict[str, int | bool]:
    return read_tmr_stats(backend)
