"""mili-support — customer support CLI."""

from __future__ import annotations

import argparse
import sys

from mili_bnn_tmr.support.contact import SupportContact, submit_support_ticket


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mili BNN-TMR customer support")
    parser.add_argument("--info", action="store_true", help="Show support contact info")
    parser.add_argument("--ticket", action="store_true", help="Submit a support ticket")
    parser.add_argument("--email", type=str, help="Customer email (required with --ticket)")
    parser.add_argument("--subject", type=str, default="SDK integration request")
    parser.add_argument("--message", type=str, default="")
    parser.add_argument("--silicon-rev", type=str, default=None)
    args = parser.parse_args(argv)

    contact = SupportContact.from_chip_spec()

    if args.ticket:
        if not args.email:
            print("Error: --email is required with --ticket", file=sys.stderr)
            return 2
        ticket = submit_support_ticket(
            args.email,
            args.subject,
            args.message or "Customer support request via mili-support CLI.",
            silicon_rev=args.silicon_rev,
        )
        print("=== Support Ticket Created ===")
        print(f"  Ticket ID:   {ticket.ticket_id}")
        print(f"  Routed to:   {contact.email}")
        print(f"  SLA:         {contact.sla_hours}h response")
        return 0

    if args.info or not any([args.ticket]):
        print("=== Mili BNN-TMR Support ===")
        print(f"  Email:       {contact.email}")
        print(f"  SLA:         {contact.sla_hours} hours")
        print(f"  Operational: {contact.validate()}")
        print(f"  Mailto:      {contact.mailto()}")
        print("\nSubmit ticket: mili-support --ticket --email you@company.com")
        return 0 if contact.validate() else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
