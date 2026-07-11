#!/usr/bin/env python3
"""Generate edge AI chip benchmark data (SRS Product 1)."""

import sys

from mili_bnn_tmr.benchmark import generate_chip_benchmark_data, summarize_benchmark

OUTPUT = "data/edge_ai_chip_benchmark.csv"


def main() -> None:
    df = generate_chip_benchmark_data()
    from pathlib import Path

    out = Path(OUTPUT)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)

    print(f"Generated {len(df)} records -> {out}")
    print("\n--- Performance by Scenario ---")
    print(summarize_benchmark(df))
    yes_pct = df["meets_spec"].value_counts(normalize=True).get("YES", 0) * 100
    print(f"\nCompliance rate: {yes_pct:.1f}%")


if __name__ == "__main__":
    sys.exit(main() or 0)
