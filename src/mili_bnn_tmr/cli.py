"""Command-line interface for Mili BNN-TMR tools."""

from __future__ import annotations

import argparse
from pathlib import Path

from mili_bnn_tmr.benchmark import (
    benchmark_compliance_rate,
    generate_chip_benchmark_data,
    summarize_benchmark,
)
from mili_bnn_tmr.config import load_chip_spec


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mili BNN-TMR Edge AI Accelerator tools",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    bench_parser = subparsers.add_parser(
        "benchmark",
        help="Generate chip benchmark data",
    )
    bench_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("data/edge_ai_chip_benchmark.csv"),
        help="Output CSV path",
    )
    bench_parser.add_argument(
        "--summary",
        action="store_true",
        help="Print summary statistics",
    )
    bench_parser.add_argument(
        "--lab",
        action="store_true",
        help="Measure benchmark from hardware backend (lab mode)",
    )
    bench_parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Use modeled synthetic benchmark data",
    )

    subparsers.add_parser("spec", help="Print chip specification")

    args = parser.parse_args()

    if args.command == "benchmark":
        mode = "synthetic" if args.synthetic else ("lab" if args.lab else "auto")
        df = generate_chip_benchmark_data(mode=mode)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(args.output, index=False)
        print(f"Generated {len(df)} records -> {args.output}")
        if args.summary:
            print("\n--- Performance by Scenario ---")
            print(summarize_benchmark(df))
            yes_pct = df["meets_spec"].value_counts(normalize=True).get("YES", 0) * 100
            print(f"\nCompliance rate: {yes_pct:.1f}%")
            print(f"Compliance rate (fn): {benchmark_compliance_rate(df):.1f}%")

    elif args.command == "spec":
        spec = load_chip_spec()
        print(f"Chip: {spec.name}")
        print(f"Technology: {spec.technology_nm}nm")
        print(f"PE count: {spec.pe_count}")
        print(f"SRAM: {spec.sram_mb} MB")
        print(f"Power: typical {spec.typical_power_w}W, max {spec.max_power_w}W")
        print(f"Frequency: {spec.base_frequency_mhz}-{spec.max_frequency_mhz} MHz")
        print("\nPower states:")
        for name, state in spec.power_states.items():
            print(
                f"  {name}: {state.frequency_mhz} MHz, "
                f"{state.power_w}W, activation {state.activation_us}us"
            )


if __name__ == "__main__":
    main()
