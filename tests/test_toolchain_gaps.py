"""Tests for toolchain gaps #13-#18."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_tflite_compiler_module():
    from mili_bnn_tmr.compiler import tflite_compiler

    assert hasattr(tflite_compiler, "parse_tflite")


def test_pytorch_compiler_module():
    from mili_bnn_tmr.compiler import pytorch_compiler

    assert hasattr(pytorch_compiler, "parse_pytorch")


def test_compile_cli_supports_formats():
    text = (ROOT / "src" / "mili_bnn_tmr" / "compile_cli.py").read_text(encoding="utf-8")
    assert "--tflite" in text
    assert "--pytorch" in text


def test_no_hardcoded_acceptance_accuracy():
    text = (ROOT / "src" / "mili_bnn_tmr" / "integration" / "e2e.py").read_text(encoding="utf-8")
    assert "97.5" not in text
    assert "measure_runtime_agreement" in text or "runtime" in text


def test_benchmark_lab_module():
    from mili_bnn_tmr.benchmark.lab import measure_lab_benchmark

    df = measure_lab_benchmark()
    assert "source" in df.columns
    assert (df["source"] == "lab").all()


def test_coverage_uses_pytest_cov():
    text = (ROOT / "src" / "mili_bnn_tmr" / "release" / "coverage.py").read_text(encoding="utf-8")
    assert "--cov=mili_bnn_tmr" in text
    assert "estimated_coverage_pct = 95" not in text


def test_firmware_bootloader_makefile():
    assert (ROOT / "firmware" / "Makefile").exists()


@pytest.mark.skipif(__import__("shutil").which("gcc") is None, reason="gcc not available")
def test_bootloader_host_test():
    import shutil
    import subprocess

    make = shutil.which("make") or shutil.which("mingw32-make")
    if not make:
        pytest.skip("make not available")
    result = subprocess.run(
        [make, "host-test"],
        cwd=ROOT / "firmware",
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr + result.stdout


def test_zephyr_module_files():
    zephyr = ROOT / "drivers" / "zephyr"
    assert (zephyr / "CMakeLists.txt").exists()
    assert (zephyr / "zephyr" / "module.yml").exists()
    assert (ROOT / "zephyr_app" / "prj.conf").exists()
    binding = zephyr / "dts" / "bindings" / "mili,bnn-tmr.yaml"
    assert "mili,bnn-tmr" in binding.read_text(encoding="utf-8")


def test_mnist_dataset_loader():
    from mili_bnn_tmr.datasets import load_mnist_subset

    imgs, labels = load_mnist_subset(8)
    assert len(imgs) == 8
    assert len(labels) == 8
