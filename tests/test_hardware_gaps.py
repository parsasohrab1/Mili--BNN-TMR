"""Tests for critical hardware gap fixes (#1-#6)."""

from __future__ import annotations

from api.python.chip_api import MiliChip
from mili_bnn_tmr.integration.backend_factory import create_backend
from mili_bnn_tmr.integration.fpga_backend import FPGABackend
from mili_bnn_tmr.integration.sim_backend import SimulatorBackend


def test_tmr_corrected_after_fault_inject():
    chip = MiliChip(use_hardware=True, backend_kind="simulator")
    chip.inject_fault(fault_lane=1)
    chip._hw.start_inference(1)
    chip._hw.wait_inference_done()
    stats = chip.get_tmr_stats()
    assert stats["disagree"] is True
    assert stats["tmr_corrected"] is True


def test_fpga_backend_type():
    fpga = FPGABackend()
    assert fpga.backend_type.value == "fpga"
    assert fpga.read_reg(0x04) & 0x01


def test_backend_factory_fpga():
    backend = create_backend("fpga")
    assert isinstance(backend, FPGABackend)


def test_backend_factory_pcie_fallback():
    backend = create_backend("pcie")
    assert backend.backend_type.value in ("pcie", "simulator")


def test_infer_hardware_tmr_flag():
    chip = MiliChip(use_hardware=True, backend_kind="simulator")
    chip.inject_fault(0)
    backend = chip.hardware_backend
    assert isinstance(backend, SimulatorBackend)
    backend.start_inference(1)
    backend.wait_inference_done()
    assert backend.get_tmr_stats()["tmr_corrected"] is True


def test_ate_hardware_bridge_import():
    from ate.hardware_bridge import SimulatorATETransport, create_ate_transport

    t = create_ate_transport()
    assert isinstance(t, SimulatorATETransport)
    r = t.run_test_program("U001", ["power_on_reset"])
    assert r.unit_id == "U001"


def test_tapeout_makefile_exists():
    from pathlib import Path

    assert (Path(__file__).resolve().parents[1] / "tapeout" / "Makefile").exists()
