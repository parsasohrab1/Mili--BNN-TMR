"""Tests for TMR majority voting."""

import numpy as np

from mili_bnn_tmr.tmr import detect_disagreement, majority_vote, tmr_execute


def test_majority_vote_scalar_agreement():
    assert majority_vote(1, 1, 0) == 1
    assert majority_vote(0, 1, 1) == 1


def test_majority_vote_all_different():
    assert majority_vote(0, 1, 2) == 1


def test_majority_vote_array():
    a = np.array([1, 0, 1])
    b = np.array([1, 1, 0])
    c = np.array([0, 1, 1])
    result = majority_vote(a, b, c)
    np.testing.assert_array_equal(result, [1, 1, 1])


def test_detect_disagreement():
    assert detect_disagreement(1, 1, 1) is False
    assert detect_disagreement(1, 0, 1) is True


def test_tmr_execute():
    call_count = 0

    def compute():
        nonlocal call_count
        call_count += 1
        return 42

    result = tmr_execute(compute)
    assert result == 42
    assert call_count == 3
