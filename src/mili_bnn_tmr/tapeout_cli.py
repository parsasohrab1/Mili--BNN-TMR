"""mili-tapeout — Phase 6 silicon tape-out validation CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    from mili_bnn_tmr.tapeout import (
        EngineeringSampleLot,
        SignoffRunner,
        SiliconCharacterization,
        TapeoutValidator,
    )

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from ate.mili_ate_program import ATEProgram, TestPhase

    parser = argparse.ArgumentParser(description="Mili BNN-TMR tape-out validation (Phase 6)")
    parser.add_argument("--acceptance", action="store_true", help="Run full acceptance validation")
    parser.add_argument("--signoff", action="store_true", help="Run DRC/LVS/timing signoff check")
    parser.add_argument("--ate", action="store_true", help="Run ATE lot simulation")
    parser.add_argument("--samples", action="store_true", help="Export engineering sample lot")
    parser.add_argument("-o", "--output", type=Path, default=Path("data/tapeout_report.json"))
    args = parser.parse_args(argv)

    if args.signoff or args.acceptance:
        runner = SignoffRunner()
        report = runner.export_report(args.output if args.signoff else args.output.with_name("signoff.json"))
        print("=== Signoff Report ===")
        print(f"  DRC:     {'PASS' if report.drc_passed else 'FAIL'}")
        print(f"  LVS:     {'PASS' if report.lvs_passed else 'FAIL'}")
        print(f"  Timing:  {'CLOSED' if report.timing_closed else 'OPEN'}")
        if not args.acceptance:
            return 0 if report.passed else 1

    if args.samples or args.acceptance:
        lot = EngineeringSampleLot.from_spec()
        lot_path = Path("data/engineering_samples.json")
        lot.export(lot_path)
        print("\n=== Engineering Samples ===")
        print(f"  Lot:     {lot.lot_id}")
        print(f"  Rev:     {lot.silicon_rev}")
        print(f"  Qty:     {lot.quantity}")
        print(f"  Yield:   {lot.yield_pct}%")
        print(f"  Export:  {lot_path}")

    if args.ate or args.acceptance:
        lot = EngineeringSampleLot.from_spec()
        ate = ATEProgram()
        unit_ids = [s.unit_id for s in lot.samples]
        ate_result = ate.run_lot(unit_ids, TestPhase.ES)
        print("\n=== ATE Test Lot ===")
        print(f"  Passed:  {ate_result['passed']}/{ate_result['total']}")
        print(f"  Yield:   {ate_result['yield_pct']}%")

    char = SiliconCharacterization.from_spec()
    print("\n=== Silicon Characterization ===")
    print(f"  Process:   {char.process}")
    print(f"  Rev:       {char.silicon_rev}")
    print(f"  Power:     {char.typical_power_w} W typical, {char.max_power_w} W max")
    print(f"  Frequency: {char.frequency_min_mhz}–{char.frequency_max_mhz} MHz")
    print(f"  TOPS/W:    {char.tops_per_watt}")
    print(f"  Yield:     {char.yield_pct}%")

    if args.acceptance:
        validation = TapeoutValidator().validate()
        print("\n=== Phase 6 Acceptance ===")
        print(f"  Signoff:   {'PASS' if validation.signoff_passed else 'FAIL'}")
        print(f"  Power:     {validation.typical_power_w} W (target ≤ 30 W)")
        print(f"  Max power: {validation.max_power_w} W (target < 50 W)")
        print(f"  Freq:      {validation.frequency_range_mhz[0]}–{validation.frequency_range_mhz[1]} MHz")
        print(f"  Yield:     {validation.yield_pct}% (target > 70%)")
        print(f"  TOPS/W:    {validation.tops_per_watt} (target ≥ 2)")
        print(f"  ES units:  {validation.engineering_samples}")
        print(f"  PASSED:    {validation.passed}")
        return 0 if validation.passed else 1

    if not any([args.signoff, args.ate, args.samples, args.acceptance]):
        parser.print_help()
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
