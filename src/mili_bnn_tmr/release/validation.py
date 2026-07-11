"""Phase 7 release acceptance validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mili_bnn_tmr.benchmark.generator import benchmark_compliance_rate, generate_chip_benchmark_data
from mili_bnn_tmr.config import ChipSpec, load_chip_spec
from mili_bnn_tmr.release.certifications import CertificationRegistry
from mili_bnn_tmr.release.coverage import SystemCoverageReportBuilder
from mili_bnn_tmr.release.packager import SDKPackager
from mili_bnn_tmr.release.qc import ProductionQC


@dataclass
class ReleaseValidationReport:
    version: str
    benchmark_compliance_pct: float
    test_coverage_pct: float
    sdk_delivery_days: int
    qc_passed: bool
    sdk_built: bool
    certifications: dict[str, Any]
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)


class ReleaseValidator:
    """Validate Phase 7 customer release acceptance criteria."""

    def __init__(self, spec: ChipSpec | None = None) -> None:
        self._spec = spec or load_chip_spec()
        self._release = self._spec.release

    def validate(self, build_sdk: bool = False) -> ReleaseValidationReport:
        df = generate_chip_benchmark_data(self._spec)
        compliance = benchmark_compliance_rate(df)

        coverage = SystemCoverageReportBuilder(
            min_coverage_pct=float(self._release.get("min_test_coverage_pct", 90))
        ).build(run_pytest=False)

        qc = ProductionQC(self._spec).run_lot_qc()
        certs = CertificationRegistry().summary()

        packager = SDKPackager()
        sdk_built = False
        sdk_path = ""
        if build_sdk:
            pkg = packager.build()
            sdk_built = Path(pkg.output_path).exists() if pkg.output_path else False
            sdk_path = pkg.output_path

        min_compliance = float(self._release.get("min_benchmark_compliance_pct", 90))
        max_delivery = int(self._release.get("sdk_delivery_days", 7))

        passed = (
            compliance >= min_compliance
            and coverage.coverage_pct >= float(self._release.get("min_test_coverage_pct", 90))
            and packager.delivery_sla_days <= max_delivery
            and qc.passed
        )

        return ReleaseValidationReport(
            version=str(self._release.get("version", "1.0.0")),
            benchmark_compliance_pct=compliance,
            test_coverage_pct=coverage.coverage_pct,
            sdk_delivery_days=packager.delivery_sla_days,
            qc_passed=qc.passed,
            sdk_built=sdk_built,
            certifications=certs,
            passed=passed,
            details={
                "coverage": coverage.to_dict(),
                "qc_pass_rate_pct": qc.pass_rate_pct,
                "sdk_path": sdk_path,
                "targets": {
                    "min_benchmark_compliance_pct": min_compliance,
                    "min_test_coverage_pct": self._release.get("min_test_coverage_pct", 90),
                    "max_sdk_delivery_days": max_delivery,
                },
            },
        )
