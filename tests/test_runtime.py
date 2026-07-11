"""Tests for MiliRuntime and chip API integration."""

import numpy as np

from api.python.chip_api import MiliChip
from mili_bnn_tmr.compiler.pipeline import compile_network
from mili_bnn_tmr.compiler.runtime import MiliRuntime
from mili_bnn_tmr.models.reference import build_mnist_bnn, generate_calibration


def test_runtime_execute(tmp_path):
    network = build_mnist_bnn()
    cal, _ = generate_calibration(network, num_samples=8)
    result = compile_network(
        network, tmp_path / "m.mili", calibration_data=cal
    )
    from mili_bnn_tmr.compiler.pipeline import load_compiled

    model = load_compiled(result.output_path)
    rt = MiliRuntime(model)
    out = rt.execute(np.random.randn(28, 28).astype(np.float32))
    assert out.shape == (10,)
    assert rt.estimate_latency_ms() > 0


def test_chip_load_mili_infer(tmp_path):
    network = build_mnist_bnn()
    cal, _ = generate_calibration(network, num_samples=8)
    mili = tmp_path / "chip.mili"
    compile_network(network, mili, calibration_data=cal)

    chip = MiliChip(use_hardware=False)
    chip.load_model(mili)
    assert chip.is_model_loaded
    status = chip.get_status()
    assert status["model_accuracy_pct"] >= 95.0
    assert status["input_shape"] == (1, 28, 28)

    result = chip.infer(np.random.randn(28, 28).astype(np.float32))
    assert result.output.shape == (10,)
    assert result.latency_ms > 0
