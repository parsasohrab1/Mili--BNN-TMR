"""Shared CSR constants and TMR status helpers (mirrors mili_regs.h)."""

from __future__ import annotations

_REG_TMR_STAT = 0x20
_TMR_DISAGREE = 1 << 0
_TMR_ERR_CNT_SHIFT = 8


def parse_tmr_stat(stat: int) -> dict[str, int | bool]:
    return {
        "disagree": bool(stat & _TMR_DISAGREE),
        "err_count": (stat >> _TMR_ERR_CNT_SHIFT) & 0xFFFF,
        "tmr_corrected": bool(stat & _TMR_DISAGREE),
    }


def read_tmr_stats(backend) -> dict[str, int | bool]:
    stat = backend.read_reg(_REG_TMR_STAT)
    return parse_tmr_stat(stat)
