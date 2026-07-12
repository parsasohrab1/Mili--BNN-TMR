"""Additional module coverage for release gate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def mnist_mili(tmp_path):
    from mili_bnn_tmr.compiler.pipeline import compile_network
    from mili_bnn_tmr.models.reference import build_mnist_bnn, generate_calibration

    network = build_mnist_bnn()
    cal, _ = generate_calibration(network, num_samples=16)
    path = tmp_path / "mnist.mili"
    compile_network(network, path, calibration_data=cal)
    return path


def test_hw_regs_decode():
    from mili_bnn_tmr.integration.hw_regs import parse_tmr_stat

    stat = parse_tmr_stat(0x03)
    assert stat["disagree"] is True
    assert stat["tmr_corrected"] is True


def test_all_backend_kinds():
    from mili_bnn_tmr.integration.backend_factory import create_backend

    for kind in ("simulator", "fpga", "stm32", "pcie"):
        b = create_backend(kind)
        assert b.backend_type.value in (kind, "simulator")


def test_pytorch_compiler_import():
    from mili_bnn_tmr.compiler import pytorch_compiler

    assert callable(pytorch_compiler.parse_pytorch)


def test_tflite_compiler_import():
    from mili_bnn_tmr.compiler import tflite_compiler

    assert callable(tflite_compiler.parse_tflite)


def test_measure_runtime_agreement(mnist_mili):
    from mili_bnn_tmr.compiler.mili_format import read_mili
    from mili_bnn_tmr.compiler.runtime import MiliRuntime
    from mili_bnn_tmr.datasets import load_mnist_subset, measure_runtime_agreement

    rt = MiliRuntime(read_mili(mnist_mili))
    imgs, _ = load_mnist_subset(8)
    acc = measure_runtime_agreement(rt, imgs)
    assert acc >= 50.0


def test_compile_model_dispatch(tmp_path):
    from mili_bnn_tmr.compiler.pipeline import compile_model

    with pytest.raises(ValueError, match="Unsupported"):
        compile_model(tmp_path / "bad.xyz", tmp_path / "out.mili")


def test_lab_benchmark_enrich():
    from mili_bnn_tmr.benchmark.lab import enrich_with_accuracy, measure_lab_benchmark

    df = measure_lab_benchmark()
    out = enrich_with_accuracy(df, 96.5)
    assert out["accuracy_pct"].iloc[0] == 96.5


@pytest.mark.parametrize(
    "module,args",
    [
        ("mili_bnn_tmr.compile_cli", ["--help"]),
        ("mili_bnn_tmr.e2e_cli", ["--help"]),
        ("mili_bnn_tmr.release_cli", ["--help"]),
        ("mili_bnn_tmr.radiation_cli", ["--help"]),
        ("mili_bnn_tmr.tapeout_cli", ["--help"]),
    ],
)
def test_cli_smoke(module, args):
    result = subprocess.run(
        [sys.executable, "-m", module, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr


def test_cli_spec_command():
    from mili_bnn_tmr.config import load_chip_spec

    spec = load_chip_spec()
    assert spec.name


def test_fpga_pcie_stm32_backend_regs():
    from mili_bnn_tmr.integration.fpga_backend import FPGABackend
    from mili_bnn_tmr.integration.pcie_backend import PCIeBackend
    from mili_bnn_tmr.integration.stm32_backend import STM32Backend

    for cls in (FPGABackend, PCIeBackend, STM32Backend):
        b = cls()
        assert b.read_reg(0x04) >= 0


def test_onnx_compiler_parse_roundtrip(tmp_path):
    from mili_bnn_tmr.compiler.onnx_compiler import parse_onnx
    from mili_bnn_tmr.models.reference import build_mnist_bnn, export_onnx

    onnx_path = tmp_path / "mnist.onnx"
    export_onnx(build_mnist_bnn(), str(onnx_path))
    net = parse_onnx(onnx_path)
    assert len(net.layers) > 0
