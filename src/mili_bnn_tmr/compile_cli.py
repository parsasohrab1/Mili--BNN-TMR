"""mili-compile — ONNX / TFLite / PyTorch / reference → .mili binary."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mili_bnn_tmr.compiler.pipeline import (
    compile_model,
    compile_network,
    compile_onnx,
    compile_pytorch,
    compile_tflite,
)
from mili_bnn_tmr.models.reference import (
    build_cifar10_bnn,
    build_custom_vision_bnn,
    build_mnist_bnn,
    generate_calibration,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compile ONNX, TFLite, PyTorch, or reference BNN models to .mili",
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
    src.add_argument("--tflite", type=Path, help="Input TFLite .tflite model path")
    src.add_argument("--pytorch", type=Path, help="Input PyTorch .pt model path")
    src.add_argument("--input", type=Path, help="Auto-detect format (.onnx/.tflite/.pt)")
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
        result = compile_onnx(args.onnx, args.output, batch_size=args.batch_size, min_accuracy_pct=args.min_accuracy)
    elif args.tflite:
        if not args.tflite.exists():
            print(f"Error: TFLite file not found: {args.tflite}", file=sys.stderr)
            return 1
        result = compile_tflite(
            args.tflite, args.output, batch_size=args.batch_size, min_accuracy_pct=args.min_accuracy
        )
    elif args.pytorch:
        if not args.pytorch.exists():
            print(f"Error: PyTorch file not found: {args.pytorch}", file=sys.stderr)
            return 1
        result = compile_pytorch(
            args.pytorch, args.output, batch_size=args.batch_size, min_accuracy_pct=args.min_accuracy
        )
    elif args.input:
        if not args.input.exists():
            print(f"Error: model not found: {args.input}", file=sys.stderr)
            return 1
        result = compile_model(args.input, args.output, batch_size=args.batch_size, min_accuracy_pct=args.min_accuracy)
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

        cal_data, cal_labels = generate_calibration(network, num_samples=args.calibration_samples)
        result = compile_network(
            network,
            args.output,
            batch_size=args.batch_size,
            calibration_data=cal_data,
            calibration_labels=cal_labels,
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
