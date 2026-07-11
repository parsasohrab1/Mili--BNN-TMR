"""mili-e2e — End-to-end integration demo CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from mili_bnn_tmr.compiler.pipeline import compile_network
from mili_bnn_tmr.models.reference import build_custom_vision_bnn, generate_calibration


def main(argv: list[str] | None = None) -> int:
    from api.python.chip_api import InterfaceType, MiliChip

    parser = argparse.ArgumentParser(description="Mili BNN-TMR E2E demo")
    parser.add_argument("--backend", choices=["simulator", "stm32"], default="simulator")
    parser.add_argument("--input-size", type=int, default=224)
    parser.add_argument("--model", type=Path, default=None)
    parser.add_argument("--acceptance", action="store_true")
    args = parser.parse_args(argv)

    model_path = args.model
    if model_path is None:
        model_path = Path("data") / f"vision_{args.input_size}.mili"
        if not model_path.exists():
            print(f"Compiling reference model for {args.input_size}×{args.input_size}...")
            network = build_custom_vision_bnn(input_size=args.input_size)
            cal, _ = generate_calibration(network, num_samples=32)
            model_path.parent.mkdir(parents=True, exist_ok=True)
            compile_network(network, model_path, calibration_data=cal)

    chip = MiliChip(interface=InterfaceType.SPI, use_hardware=True)
    chip.load_model(model_path)

    print("=== Mili BNN-TMR E2E Demo ===")
    status = chip.get_status()
    print(f"Backend:  {status['backend']}")
    print(f"Model:    {model_path}")
    print(f"Shape:    {status['input_shape']}")

    if args.acceptance:
        report = chip.run_acceptance_test()
        print("\n--- Acceptance Report ---")
        print(f"  E2E latency:    {report.e2e_latency_ms} ms  (target < 10)")
        print(f"  Energy:         {report.energy_mj} mJ       (target < 2)")
        print(f"  Accuracy:       {report.accuracy_pct}%       (target ≥ 95)")
        print(f"  Idle saving:    {report.idle_power_saving_pct}%    (target ≥ 40)")
        print(f"  DPM switch:     {report.dpm_switch_us} µs     (target < 100)")
        print(f"  PASSED:         {report.passed}")
        return 0 if report.passed else 1

    result = chip.capture_and_classify()
    print(f"\nClass:      {result.class_name} (id={result.class_id})")
    print(f"Confidence: {result.confidence:.2%}")
    print(f"Latency:    {result.latency_ms:.2f} ms")
    print(f"Energy:     {result.energy_mj:.3f} mJ")

    img = np.random.randn(args.input_size, args.input_size).astype(np.float32)
    infer = chip.infer(img)
    print(f"\nDirect infer: {infer.latency_ms:.2f} ms ({infer.backend})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
