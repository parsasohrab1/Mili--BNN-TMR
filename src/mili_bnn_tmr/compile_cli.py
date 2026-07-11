"""mili-compile — ONNX / reference model → .mili binary compiler."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mili_bnn_tmr.compiler.pipeline import compile_network, compile_onnx
from mili_bnn_tmr.models.reference import (
    build_cifar10_bnn,
    build_custom_vision_bnn,
    build_mnist_bnn,
    generate_calibration,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compile ONNX or reference BNN models to .mili binary",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Output .mili file path",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1,
        help="Batch size for scheduling",
    )
    parser.add_argument(
        "--min-accuracy",
        type=float,
        default=95.0,
        help="Minimum quantization accuracy %% (default: 95)",
    )
    parser.add_argument(
        "--calibration-samples",
        type=int,
        default=64,
        help="Number of calibration samples",
    )

    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--onnx", type=Path, help="Input ONNX model path")
    src.add_argument(
        "--reference",
        choices=["mnist", "cifar10", "vision"],
        help="Build from reference architecture",
    )
    parser.add_argument(
        "--input-size",
        type=int,
        default=224,
        help="Input spatial size for --reference vision (32–224)",
    )
    parser.add_argument(
        "--num-classes",
        type=int,
        default=10,
        help="Output classes for --reference vision",
    )

    args = parser.parse_args(argv)

    if args.onnx:
        if not args.onnx.exists():
            print(f"Error: ONNX file not found: {args.onnx}", file=sys.stderr)
            return 1
        result = compile_onnx(
            args.onnx,
            args.output,
            batch_size=args.batch_size,
            min_accuracy_pct=args.min_accuracy,
        )
    else:
        if args.reference == "mnist":
            network = build_mnist_bnn()
        elif args.reference == "cifar10":
            network = build_cifar10_bnn()
        else:
            network = build_custom_vision_bnn(
                input_size=args.input_size,
                num_classes=args.num_classes,
            )

        cal_data, _ = generate_calibration(
            network, num_samples=args.calibration_samples
        )
        result = compile_network(
            network,
            args.output,
            batch_size=args.batch_size,
            calibration_data=cal_data,
            min_accuracy_pct=args.min_accuracy,
        )

    print(f"Compiled: {result.output_path}")
    print(f"  Layers:    {result.report.layer_count}")
    print(f"  Accuracy:  {result.accuracy_pct}%")
    print(f"  Weights:   {result.report.weight_bits_total:,} bits")
    print(f"  Instrs:    {len(result.plan.instructions)}")
    print(f"  SRAM:      {result.plan.sram.weights_size / 1e6:.2f} MB (weights)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
