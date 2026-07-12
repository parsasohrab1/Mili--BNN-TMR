"""Operational support channel for Mili BNN-TMR customers."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from mili_bnn_tmr.config import load_chip_spec

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
_DEFAULT_TICKET_DIR = Path("support/tickets")


@dataclass(frozen=True)
class SupportContact:
    email: str
    sla_hours: int
    vendor: str = "Mili Semiconductor"

    @classmethod
    def from_chip_spec(cls) -> SupportContact:
        spec = load_chip_spec()
        release = spec.release
        email = str(release.get("support_email", "support@mili-chip.com"))
        sla = int(release.get("support_sla_hours", 24))
        return cls(email=email, sla_hours=sla)

    def validate(self) -> bool:
        return bool(_EMAIL_RE.match(self.email))

    def mailto(self, subject: str = "Mili BNN-TMR SDK Support", body: str = "") -> str:
        params = []
        if subject:
            params.append(f"subject={quote(subject)}")
        if body:
            params.append(f"body={quote(body)}")
        query = f"?{'&'.join(params)}" if params else ""
        return f"mailto:{self.email}{query}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "email": self.email,
            "sla_hours": self.sla_hours,
            "vendor": self.vendor,
            "operational": self.validate(),
            "mailto": self.mailto(),
        }


@dataclass
class SupportTicket:
    ticket_id: str
    customer_email: str
    subject: str
    message: str
    silicon_rev: str
    sdk_version: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def submit_support_ticket(
    customer_email: str,
    subject: str,
    message: str,
    *,
    silicon_rev: str | None = None,
    ticket_dir: Path | None = None,
) -> SupportTicket:
    """Persist a support ticket for engineering follow-up within SLA."""
    if not _EMAIL_RE.match(customer_email):
        raise ValueError(f"Invalid customer email: {customer_email}")

    contact = SupportContact.from_chip_spec()
    if not contact.validate():
        raise RuntimeError(f"Support channel not operational: {contact.email}")

    spec = load_chip_spec()
    ticket = SupportTicket(
        ticket_id=f"MILI-{uuid.uuid4().hex[:8].upper()}",
        customer_email=customer_email,
        subject=subject.strip(),
        message=message.strip(),
        silicon_rev=silicon_rev or spec.silicon_rev,
        sdk_version=str(spec.release.get("version", "1.0.0")),
    )

    out_dir = ticket_dir or _DEFAULT_TICKET_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{ticket.ticket_id}.json"
    path.write_text(json.dumps(ticket.to_dict(), indent=2), encoding="utf-8")
    return ticket
