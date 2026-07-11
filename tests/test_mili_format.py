"""Tests for .mili binary format."""

from mili_bnn_tmr.compiler.mili_format import read_mili, write_mili
from mili_bnn_tmr.compiler.optimizer import optimize
from mili_bnn_tmr.compiler.quantizer import quantize_network
from mili_bnn_tmr.models.reference import build_mnist_bnn


def test_write_read_roundtrip(tmp_path):
    network = build_mnist_bnn()
    quantize_network(network)
    plan = optimize(network)
    out = tmp_path / "test.mili"
    write_mili(out, plan, accuracy_pct=97.5)

    model = read_mili(out)
    assert model.name == "test"
    assert model.input_shape == (1, 28, 28)
    assert model.output_shape == (10,)
    assert len(model.instructions) > 0
    assert len(model.network.layers) == len(network.layers)


def test_mili_magic(tmp_path):
    bad = tmp_path / "bad.mili"
    bad.write_bytes(b"BAD!")
    try:
        read_mili(bad)
        assert False, "should raise"
    except ValueError as e:
        assert "magic" in str(e).lower()
