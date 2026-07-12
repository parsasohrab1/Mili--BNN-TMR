"""System test coverage via pytest-cov."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[3]
_COV_JSON = _ROOT / "coverage.json"


@dataclass
class SubsystemCoverage:
    name: str
    test_files: int
    estimated_coverage_pct: float


@dataclass
class SystemCoverageReport:
    total_tests: int
    subsystems: list[SubsystemCoverage] = field(default_factory=list)
    coverage_pct: float = 0.0
    meets_target: bool = False
    lines_covered: int = 0
    lines_total: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_tests": self.total_tests,
            "coverage_pct": self.coverage_pct,
            "meets_target": self.meets_target,
            "lines_covered": self.lines_covered,
            "lines_total": self.lines_total,
            "subsystems": [
                {"name": s.name, "tests": s.test_files, "coverage_pct": s.estimated_coverage_pct}
                for s in self.subsystems
            ],
        }


class SystemCoverageReportBuilder:
    """Build system coverage report using pytest-cov."""

    def __init__(self, min_coverage_pct: float = 90.0) -> None:
        self._min = min_coverage_pct
        self._tests_dir = _ROOT / "tests"

    def build(self, run_pytest: bool = True) -> SystemCoverageReport:
        total_tests = self._count_tests()
        coverage_pct, lines_cov, lines_tot, per_file = (
            self._run_pytest_cov() if run_pytest else self._load_cached_cov()
        )

        subsystems = self._subsystem_breakdown(per_file)

        return SystemCoverageReport(
            total_tests=total_tests,
            subsystems=subsystems,
            coverage_pct=coverage_pct,
            meets_target=coverage_pct >= self._min,
            lines_covered=lines_cov,
            lines_total=lines_tot,
        )

    def _count_tests(self) -> int:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests", "-q", "--collect-only"],
            cwd=_ROOT,
            capture_output=True,
            text=True,
        )
        for line in result.stdout.splitlines():
            if " test" in line and "tests" in line:
                parts = line.strip().split()
                if parts and parts[0].isdigit():
                    return int(parts[0])
        return len(list(self._tests_dir.glob("test_*.py")))

    def _run_pytest_cov(self) -> tuple[float, int, int, dict[str, float]]:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests",
                "-q",
                "--cov=mili_bnn_tmr",
                "--cov=api",
                "--cov-report=json:coverage.json",
                "--cov-fail-under=0",
            ],
            cwd=_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        return self._parse_cov_json(_COV_JSON)

    def _load_cached_cov(self) -> tuple[float, int, int, dict[str, float]]:
        if _COV_JSON.exists() and _COV_JSON.stat().st_size > 0:
            return self._parse_cov_json(_COV_JSON)
        return 0.0, 0, 0, {}

    def _parse_cov_json(self, path: Path) -> tuple[float, int, int, dict[str, float]]:
        if not path.exists():
            return 0.0, 0, 0, {}
        data = json.loads(path.read_text(encoding="utf-8"))
        totals = data.get("totals", {})
        pct = round(float(totals.get("percent_covered", 0.0)), 1)
        covered = int(totals.get("covered_lines", 0))
        total = int(totals.get("num_statements", 0))
        per_file: dict[str, float] = {}
        for fname, stats in data.get("files", {}).items():
            per_file[fname] = float(stats.get("summary", {}).get("percent_covered", 0.0))
        return pct, covered, total, per_file

    def _subsystem_breakdown(self, per_file: dict[str, float]) -> list[SubsystemCoverage]:
        groups = {
            "compiler": "compiler",
            "integration": "integration",
            "radiation": "radiation",
            "tapeout": "tapeout",
            "release": "release",
            "benchmark": "benchmark",
        }
        subsystems: list[SubsystemCoverage] = []
        for name, token in groups.items():
            files = [f for f in per_file if token in f.replace("\\", "/")]
            if files:
                pct = round(sum(per_file[f] for f in files) / len(files), 1)
            else:
                pct = 0.0
            test_files = len(list(self._tests_dir.glob(f"test_*{name[:4]}*.py")))
            subsystems.append(
                SubsystemCoverage(name=name, test_files=test_files, estimated_coverage_pct=pct)
            )
        return subsystems
