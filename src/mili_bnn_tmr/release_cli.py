"""mili-release — Phase 7 customer SDK release CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    from mili_bnn_tmr.release import (
        CertificationRegistry,
        ProductionQC,
        ReleaseValidator,
        SDKPackager,
        SystemCoverageReportBuilder,
    )
    from mili_bnn_tmr.benchmark import benchmark_compliance_rate, generate_chip_benchmark_data

    parser = argparse.ArgumentParser(description="Mili BNN-TMR SDK release v1.0")
    parser.add_argument("--acceptance", action="store_true", help="Run full release acceptance")
    parser.add_argument("--build-sdk", action="store_true", help="Build SDK tarball")
    parser.add_argument("--qc", action="store_true", help="Run production QC report")
    parser.add_argument("--certs", action="store_true", help="List certifications")
    parser.add_argument("-o", "--output", type=Path, default=Path("dist"))
    args = parser.parse_args(argv)

    if args.certs or args.acceptance:
        certs = CertificationRegistry().summary()
        print("=== Certifications ===")
        for item in certs["items"]:
            print(f"  {item['standard']:25s} {item['status']:12s} {item.get('level', '')}")
        if not args.acceptance:
            return 0

    if args.qc or args.acceptance:
        qc = ProductionQC().run_lot_qc()
        print("\n=== Production QC ===")
        print(f"  Lot:       {qc.lot_id}")
        print(f"  Checks:    {len(qc.checks)}")
        print(f"  Pass rate: {qc.pass_rate_pct}%")
        print(f"  PASSED:    {qc.passed}")

    df = generate_chip_benchmark_data()
    compliance = benchmark_compliance_rate(df)
    print("\n=== Benchmark Compliance ===")
    print(f"  Records:    {len(df)}")
    print(f"  Compliance: {compliance}% (target > 90%)")

    coverage = SystemCoverageReportBuilder().build(run_pytest=False)
    print("\n=== System Test Coverage ===")
    print(f"  Tests:      {coverage.total_tests}")
    print(f"  Coverage:   {coverage.coverage_pct}% (target > 90%)")
    for sub in coverage.subsystems:
        print(f"    {sub.name:20s} {sub.estimated_coverage_pct}%")

    if args.build_sdk or args.acceptance:
        pkg = SDKPackager().build(args.output)
        print("\n=== SDK Package ===")
        print(f"  Version:  {pkg.version}")
        print(f"  Archive:  {pkg.output_path}")
        included = sum(1 for c in pkg.components if c.included)
        print(f"  Components: {included}/{len(pkg.components)}")

    if args.acceptance:
        report = ReleaseValidator().validate(build_sdk=True)
        print("\n=== Phase 7 Release Acceptance (v1.0) ===")
        print(f"  Version:           {report.version}")
        print(f"  Benchmark:         {report.benchmark_compliance_pct}% (target > 90%)")
        print(f"  Test coverage:     {report.test_coverage_pct}% (target > 90%)")
        print(f"  SDK delivery SLA:  {report.sdk_delivery_days} days (target < 7)")
        print(f"  QC:                {'PASS' if report.qc_passed else 'FAIL'}")
        print(f"  SDK built:         {report.sdk_built}")
        print(f"  PASSED:            {report.passed}")
        return 0 if report.passed else 1

    if not any([args.acceptance, args.build_sdk, args.qc, args.certs]):
        parser.print_help()

    return 0


if __name__ == "__main__":
    sys.exit(main())
