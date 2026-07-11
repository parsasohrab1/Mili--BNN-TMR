#!/usr/bin/env python3
"""Quick-start example — classify with Mili BNN-TMR SDK."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.python.chip_api import MiliChip  # noqa: E402


def main() -> int:
    chip = MiliChip(use_hardware=True)

    model = ROOT / "data" / "mnist.mili"
    if not model.exists():
        print("Run: mili-compile --reference mnist -o data/mnist.mili")
        return 1

    chip.load_model(model)
    result = chip.capture_and_classify()
    print(f"Class: {result.class_name} ({result.confidence:.1%})")
    print(f"Latency: {result.latency_ms:.2f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
