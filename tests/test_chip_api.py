"""Tests for high-level chip API."""

import numpy as np
import pytest

from api.python.chip_api import InferenceResult, InterfaceType, MiliChip


def test_chip_status():
    chip = MiliChip(interface=InterfaceType.SPI)
    status = chip.get_status()
    assert status["interface"] == "spi"
    assert status["model_loaded"] is False


def test_infer_requires_model(tmp_path):
    chip = MiliChip(use_hardware=False)
    network = __import__(
        "mili_bnn_tmr.models.reference", fromlist=["build_mnist_bnn"]
    ).build_mnist_bnn()
    cal, _ = __import__(
        "mili_bnn_tmr.models.reference", fromlist=["generate_calibration"]
    ).generate_calibration(network, num_samples=8)
    from mili_bnn_tmr.compiler.pipeline import compile_network

    model = tmp_path / "model.mili"
    compile_network(network, model, calibration_data=cal)

    chip.load_model(model)
    assert chip.is_model_loaded

    result = chip.infer(np.random.randn(28, 28).astype(np.float32))
    assert isinstance(result, InferenceResult)
    assert result.output.shape == (10,)


def test_infer_without_model_raises():
    chip = MiliChip()
    with pytest.raises(RuntimeError, match="No model loaded"):
        chip.infer(np.array([1.0]))


def test_load_missing_model_raises():
    chip = MiliChip()
    with pytest.raises(FileNotFoundError):
        chip.load_model("nonexistent.mili")


def test_load_unsupported_format_raises(tmp_path):
    chip = MiliChip()
    bad = tmp_path / "model.xyz"
    bad.write_text("stub")
    with pytest.raises(ValueError, match="Unsupported"):
        chip.load_model(bad)
