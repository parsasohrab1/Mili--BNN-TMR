"""Triple Modular Redundancy (TMR) for SEU fault tolerance."""

from __future__ import annotations

from typing import TypeVar

import numpy as np

T = TypeVar("T", int, float, bool, np.ndarray)


def majority_vote(a: T, b: T, c: T) -> T:
    """Return the majority value from three redundant module outputs."""
    if isinstance(a, np.ndarray):
        return np.where(a == b, a, np.where(a == c, a, b))
    return _vote_scalar(a, b, c)


def _vote_scalar(a: T, b: T, c: T) -> T:
    if a == b or a == c:
        return a
    return b


def tmr_execute(fn, *args, **kwargs):
    """Execute a function three times and return the majority-voted result."""
    results = [fn(*args, **kwargs) for _ in range(3)]
    return majority_vote(results[0], results[1], results[2])


def detect_disagreement(a: T, b: T, c: T) -> bool:
    """Detect whether any TMR lane disagrees (matches RTL tmr_voter semantics)."""
    if isinstance(a, np.ndarray):
        return not (np.array_equal(a, b) and np.array_equal(a, c))
    return not (a == b == c)
