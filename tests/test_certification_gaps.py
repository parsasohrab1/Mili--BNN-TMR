"""Tests for certification gaps #19-#22."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mili_bnn_tmr.integration.backend_factory import create_backend
from mili_bnn_tmr.integration.fpga_backend import FPGABackend
from mili_bnn_tmr.integration.pcie_backend import PCIeBackend
from mili_bnn_tmr.integration.stm32_backend import STM32Backend
from mili_bnn_tmr.integration.tmr_fault import inject_tmr_fault_csr
from mili_bnn_tmr.radiation import (
    HardwareRadiationCampaign,
    PhysicalBeamProtocol,
    RadiationValidator,
)
from mili_bnn_tmr.release import DO254EvidenceBuilder
from mili_bnn_tmr.release.certifications import CertificationRegistry, CertStatus


ROOT = Path(__file__).resolve().parents[1]


def test_do254_evidence_package_complete():
    pkg = DO254EvidenceBuilder().build()
    assert pkg.dal_level == "DAL-B"
    assert pkg.completion_pct >= 90.0
    assert pkg.ready_for_review
    assert len(pkg.artifacts) >= 8


def test_do254_evidence_export(tmp_path):
    path = DO254EvidenceBuilder().export(tmp_path / "do254")
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["dal_level"] == "DAL-B"


def test_do254_traceability_matrix_exists():
    p = ROOT / "release" / "certifications" / "do254_evidence" / "traceability_matrix.yaml"
    assert p.exists()
    assert "FR-2" in p.read_text(encoding="utf-8")


def test_ecss_physical_beam_pending():
    registry = CertificationRegistry()
    ecss = next(c for c in registry.certifications if "ECSS" in c.standard)
    assert ecss.status == CertStatus.CERTIFIED_SOFTWARE
    beam = PhysicalBeamProtocol().evaluate(software_seu_pct=99.5)
    assert beam.physical_status.value == "pending"
    assert len(beam.plans) >= 2
    assert any(p.profile.value == "cobalt_60" for p in beam.plans)


def test_csr_fault_inject_production_backends():
    for backend in (FPGABackend(), PCIeBackend(), STM32Backend()):
        assert hasattr(backend, "inject_tmr_fault")
        assert hasattr(backend, "clear_tmr_fault")
        backend.inject_tmr_fault(1)
        backend.start_inference(1)
        assert backend.wait_inference_done()
        stats = backend.get_tmr_stats()
        assert stats["disagree"] is True
        backend.clear_tmr_fault()


def test_tmr_fault_csr_helper():
    from mili_bnn_tmr.integration.sim_backend import SimulatorBackend

    b = SimulatorBackend()
    inject_tmr_fault_csr(b, 2)
    b.start_inference(1)
    b.wait_inference_done()
    assert b.get_tmr_stats()["disagree"] is True


def test_hardware_radiation_campaign():
    campaign = HardwareRadiationCampaign()
    report = campaign.run_on_lot(max_units=3)
    assert report.units_tested == 3
    assert report.overall_correction_pct >= 99.0
    assert report.passed


def test_radiation_validator_hardware_csr_path():
    from mili_bnn_tmr.integration.backend_factory import create_backend

    backend = create_backend("fpga")
    validator = RadiationValidator(backend=backend)
    pct = validator.run_hardware_fault_injection(num_trials=30)
    assert pct >= 99.0


def test_ecss_yaml_documents_physical_pending():
    text = (ROOT / "release" / "certifications" / "ecss.yaml").read_text(encoding="utf-8")
    assert "physical_test_status: pending" in text
    assert "cobalt_60" in text
    assert "proton_beam" in text
