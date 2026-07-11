"""End-to-end integration tests (Phase 4)."""

import numpy as np
import pytest

from api.python.chip_api import MiliChip, InterfaceType
from mili_bnn_tmr.compiler.pipeline import compile_network
from mili_bnn_tmr.integration.e2e import E2EPipeline, ImagePreprocessor
from mili_bnn_tmr.integration.sim_backend import SimulatorBackend
from mili_bnn_tmr.models.reference import build_mnist_bnn, generate_calibration
from mili_bnn_tmr.power.dpm import PowerMode


@pytest.fixture
def mnist_mili(tmp_path):
    network = build_mnist_bnn()
    cal, _ = generate_calibration(network, num_samples=16)
    path = tmp_path / "mnist.mili"
    compile_network(network, path, calibration_data=cal)
    return path


def test_image_preprocessor():
    prep = ImagePreprocessor((1, 28, 28))
    img = np.random.randint(0, 255, (28, 28)).astype(np.float32)
    out = prep.process(img)
    assert out.shape == (1, 28, 28)


def test_e2e_pipeline_classify():
    pipeline = E2EPipeline.from_backend_type("simulator", input_shape=(1, 28, 28))
    img = np.random.randn(28, 28).astype(np.float32)
    result = pipeline.classify(img)
    assert 0 <= result.class_id < 10
    assert result.latency_ms >= 0
    assert result.backend == "simulator"


def test_e2e_capture_and_classify():
    pipeline = E2EPipeline.from_backend_type("simulator", input_shape=(1, 64, 64))
    result = pipeline.capture_and_classify()
    assert result.confidence > 0


def test_dpm_switch_under_100us():
    backend = SimulatorBackend()
    result = backend.set_power_mode(PowerMode.TURBO)
    assert result.switch_time_us < 100


def test_dpm_idle_power_saving():
    backend = SimulatorBackend()
    backend.set_power_mode(PowerMode.NORMAL)
    result = backend.set_power_mode(PowerMode.IDLE)
    assert result.power_saving_pct >= 40


def test_chip_hardware_infer(mnist_mili):
    chip = MiliChip(use_hardware=True)
    chip.load_model(mnist_mili)
    result = chip.infer(np.random.randn(28, 28).astype(np.float32))
    assert result.backend == "simulator"
    assert result.output.shape == (10,)
    assert result.energy_mj >= 0


def test_chip_capture_and_classify(mnist_mili):
    chip = MiliChip(use_hardware=True)
    chip.load_model(mnist_mili)
    result = chip.capture_and_classify()
    assert result.latency_ms >= 0


def test_acceptance_criteria(mnist_mili):
    chip = MiliChip(use_hardware=True)
    chip.load_model(mnist_mili)
    report = chip.run_acceptance_test()
    assert report.e2e_latency_ms < 10
    assert report.energy_mj < 2
    assert report.accuracy_pct >= 95
    assert report.idle_power_saving_pct >= 40
    assert report.dpm_switch_us < 100
    assert report.passed
