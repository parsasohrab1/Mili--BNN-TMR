#!/usr/bin/env python3
"""Ensure data/mnist.mili exists (compile if missing)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "data" / "mnist.mili"


def main() -> int:
    if MODEL.exists():
        print(f"OK: {MODEL} ({MODEL.stat().st_size} bytes)")
        return 0

    MODEL.parent.mkdir(parents=True, exist_ok=True)
    print(f"Compiling reference MNIST model → {MODEL}")
    subprocess.run(
        ["mili-compile", "--reference", "mnist", "-o", str(MODEL)],
        check=True,
    )
    print(f"Created {MODEL} ({MODEL.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
