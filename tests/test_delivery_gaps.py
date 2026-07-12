"""Tests for delivery gaps #23-#28."""

from __future__ import annotations

import json
from pathlib import Path

from api.python.chip_api import MiliChip
from mili_bnn_tmr.config import load_chip_spec
from mili_bnn_tmr.release import SDKPackager
from mili_bnn_tmr.silicon_revision import SiliconRevision
from mili_bnn_tmr.support import SupportContact, submit_support_ticket

ROOT = Path(__file__).resolve().parents[1]


def test_release_workflow_publishes_sdk(tmp_path):
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "mili-bnn-tmr-sdk" in workflow
    assert "action-gh-release" in workflow
    assert "mili-release --build-sdk" in workflow

    pkg = SDKPackager().build(tmp_path)
    archive = Path(pkg.output_path)
    assert archive.name.startswith("mili-bnn-tmr-sdk-")
    assert archive.suffix == ".gz"


def test_mnist_mili_in_repo_or_compilable():
    model = ROOT / "data" / "mnist.mili"
    assert model.exists(), "Run: python scripts/ensure_mnist_model.py"
    assert model.stat().st_size > 1000

    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "!data/*.mili" in gitignore


def test_support_email_operational():
    contact = SupportContact.from_chip_spec()
    assert contact.email == "support@mili-chip.com"
    assert contact.validate() is True
    assert contact.sla_hours == 24
    assert contact.mailto().startswith("mailto:support@mili-chip.com")


def test_support_ticket_intake(tmp_path):
    ticket = submit_support_ticket(
        "customer@aerospace.com",
        "SPI bring-up",
        "Need help with STM32H7 wiring.",
        ticket_dir=tmp_path,
    )
    path = tmp_path / f"{ticket.ticket_id}.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["silicon_rev"] == "A0"


def test_readme_documents_seven_phases_and_cli():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for phase in range(1, 8):
        assert f"**{phase}**" in readme or f"Phase {phase}" in readme
    for cmd in (
        "mili-compile",
        "mili-benchmark",
        "mili-e2e",
        "mili-radiation",
        "mili-tapeout",
        "mili-release",
        "mili-support",
    ):
        assert cmd in readme
    assert "GitHub Releases" in readme


def test_chip_spec_loader_complete_fields():
    spec = load_chip_spec()
    assert spec.packaging == "BGA-484"
    assert len(spec.interfaces) >= 4
    assert spec.operating_temp_c[0] == -40
    assert spec.operating_temp_c[1] == 85


def test_silicon_revision_api_and_docs():
    chip = MiliChip(use_hardware=False)
    info = chip.get_silicon_info()
    assert info["silicon_rev"] == "A0"
    assert info["next_rev"] == "A1"
    assert info["packaging"] == "BGA-484"

    status = chip.get_status()
    assert status["silicon_rev"] == "A0"
    assert status["packaging"] == "BGA-484"
    assert status["operating_temp_c"] == [-40, 85]

    rev = SiliconRevision.from_string("A0")
    assert rev.next_revision() == SiliconRevision.A1

    doc = (ROOT / "docs" / "HARDWARE_REVISION.md").read_text(encoding="utf-8")
    assert "A0" in doc and "A1" in doc


def test_ci_ensures_mnist_model():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "data/mnist.mili" in ci
    assert "mili-compile --reference mnist" in ci
