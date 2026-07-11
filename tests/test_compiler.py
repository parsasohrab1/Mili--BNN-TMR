"""Tests for compiler pipeline and optimizer."""

from mili_bnn_tmr.compiler.optimizer import optimize
from mili_bnn_tmr.compiler.pipeline import compile_network
from mili_bnn_tmr.models.reference import (
    build_cifar10_bnn,
    build_custom_vision_bnn,
    build_mnist_bnn,
    generate_calibration,
)


def test_optimize_mnist():
    network = build_mnist_bnn()
    plan = optimize(network)
    assert len(plan.instructions) > 0
    assert plan.sram.weights_size > 0
    assert plan.tile_config["pe_rows"] == 8


def test_compile_mnist(tmp_path):
    network = build_mnist_bnn()
    cal, _ = generate_calibration(network, num_samples=32)
    result = compile_network(
        network,
        tmp_path / "mnist.mili",
        calibration_data=cal,
        min_accuracy_pct=95.0,
    )
    assert result.output_path.exists()
    assert result.accuracy_pct >= 95.0
    assert result.report.layer_count <= 20


def test_compile_cifar10(tmp_path):
    network = build_cifar10_bnn()
    cal, _ = generate_calibration(network, num_samples=32)
    result = compile_network(
        network,
        tmp_path / "cifar.mili",
        calibration_data=cal,
    )
    assert result.output_path.stat().st_size > 1000


def test_compile_custom_vision(tmp_path):
    network = build_custom_vision_bnn(input_size=64, num_classes=5)
    cal, _ = generate_calibration(network, num_samples=16)
    result = compile_network(
        network,
        tmp_path / "vision.mili",
        calibration_data=cal,
    )
    assert result.plan.network.output_shape == (5,)
