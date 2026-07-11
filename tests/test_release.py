"""Tests for Phase 7 production release and SDK."""

from __future__ import annotations

from pathlib import Path

import pytest

from mili_bnn_tmr.benchmark import benchmark_compliance_rate, generate_chip_benchmark_data
from mili_bnn_tmr.config import load_chip_spec
from mili_bnn_tmr.release import (
    CertificationRegistry,
    ProductionQC,
    ReleaseValidator,
    SDKPackager,
    SystemCoverageReportBuilder,
)


def test_release_section_in_spec():
    spec = load_chip_spec()
    assert spec.release["version"] == "1.0.0"
    assert spec.release["sdk_delivery_days"] < 7


def test_benchmark_compliance_above_90():
    df = generate_chip_benchmark_data()
    rate = benchmark_compliance_rate(df)
    assert rate > 90.0


def test_system_coverage_above_90():
    report = SystemCoverageReportBuilder(min_coverage_pct=90).build(run_pytest=False)
    assert report.coverage_pct > 90.0
    assert report.meets_target


def test_production_qc_passes():
    qc = ProductionQC().run_lot_qc()
    assert qc.passed
    assert qc.pass_rate_pct == 100.0
    assert len(qc.checks) >= 5


def test_certifications_loaded():
    registry = CertificationRegistry()
    summary = registry.summary()
    assert summary["total"] >= 2
    assert summary["certified"] >= 1


def test_sdk_packager_builds(tmp_path):
    pkg = SDKPackager(version="1.0.0").build(tmp_path)
    assert Path(pkg.output_path).exists()
    included = [c for c in pkg.components if c.included]
    assert len(included) >= 5
    names = {c.name for c in included}
    assert "drivers" in names
    assert "api_python" in names
    assert "docs" in names


def test_release_acceptance():
    report = ReleaseValidator().validate(build_sdk=False)
    assert report.benchmark_compliance_pct > 90.0
    assert report.test_coverage_pct > 90.0
    assert report.sdk_delivery_days < 7
    assert report.qc_passed
    assert report.passed


def test_documentation_exists():
    docs = Path(__file__).resolve().parents[1] / "docs"
    assert (docs / "DATASHEET.md").exists()
    assert (docs / "API_REFERENCE.md").exists()
    assert (docs / "INTEGRATION.md").exists()
    assert (docs / "RELEASE.md").exists()


def test_sdk_manifest_exists():
    manifest = Path(__file__).resolve().parents[1] / "release" / "sdk_manifest.yaml"
    assert manifest.exists()
