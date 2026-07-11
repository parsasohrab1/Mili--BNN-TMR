"""TMR fault tolerance module."""

from mili_bnn_tmr.tmr.voter import detect_disagreement, majority_vote, tmr_execute

__all__ = ["majority_vote", "tmr_execute", "detect_disagreement"]
