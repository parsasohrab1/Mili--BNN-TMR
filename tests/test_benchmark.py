"""Tests for benchmark data generation."""

import pandas as pd

from mili_bnn_tmr.benchmark import generate_chip_benchmark_data, summarize_benchmark
from mili_bnn_tmr.config import load_chip_spec


def test_generate_benchmark_returns_dataframe():
    df = generate_chip_benchmark_data()
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0


def test_benchmark_has_required_columns():
    df = generate_chip_benchmark_data()
    required = {
        "scenario",
        "batch_size",
        "frequency_mhz",
        "power_watts",
        "latency_ms",
        "accuracy_pct",
        "tmr_effectiveness_pct",
        "meets_spec",
    }
    assert required.issubset(df.columns)


def test_benchmark_scenarios_match_spec():
    spec = load_chip_spec()
    df = generate_chip_benchmark_data(spec)
    assert set(df["scenario"].unique()) == set(spec.benchmark["scenarios"])


def test_summarize_benchmark():
    df = generate_chip_benchmark_data()
    summary = summarize_benchmark(df)
    assert len(summary) == len(df["scenario"].unique())


def test_reproducible_with_seed():
    df1 = generate_chip_benchmark_data()
    df2 = generate_chip_benchmark_data()
    pd.testing.assert_frame_equal(df1, df2)
