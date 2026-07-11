"""Tests for BNN quantizer."""

import numpy as np

from mili_bnn_tmr.compiler.quantizer import (
    binary_to_sign,
    estimate_accuracy,
    float_to_binary,
    forward_bnn,
    quantize_network,
)
from mili_bnn_tmr.models.reference import build_mnist_bnn, generate_calibration


def test_float_to_binary():
    w = np.array([-1.0, 0.0, 1.0, 2.0], dtype=np.float32)
    b = float_to_binary(w)
    assert list(b) == [0, 1, 1, 1]


def test_binary_to_sign():
    b = np.array([0, 1, 0, 1], dtype=np.uint8)
    s = binary_to_sign(b)
    np.testing.assert_array_equal(s, [-1, 1, -1, 1])


def test_quantize_preserves_forward_agreement():
    network = build_mnist_bnn()
    cal, _ = generate_calibration(network, num_samples=16)
    acc = estimate_accuracy(network, cal)
    quantize_network(network)
    acc_after = estimate_accuracy(network, cal)
    assert acc_after >= 95.0


def test_forward_bnn_output_shape():
    network = build_mnist_bnn()
    quantize_network(network)
    x = np.random.randn(1, 28, 28).astype(np.float32)
    out = forward_bnn(network, x)
    assert out.shape == (10,)
