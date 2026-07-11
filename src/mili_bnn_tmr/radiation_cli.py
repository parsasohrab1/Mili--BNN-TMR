"""mili-radiation — Phase 5 radiation / SEU validation CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from api.python.chip_api import MiliChip
    from mili_bnn_tmr.radiation import RadiationProfile, RadiationValidator
    from mili_bnn_tmr.radiation.seu_emulator import SEUEmulator

    parser = argparse.ArgumentParser(description="Mili BNN-TMR radiation validation (FR-2)")
    parser.add_argument(
        "--profile",
        choices=[p.value for p in RadiationProfile],
        default=RadiationProfile.COBALT_60.value,
    )
    parser.add_argument("--trials", type=int, default=1000)
    parser.add_argument("--log", type=Path, default=Path("data/seu_log.json"))
    parser.add_argument("--acceptance", action="store_true", help="Run full acceptance validation")
    parser.add_argument("--mtbf-only", action="store_true", help="Print MTBF for all profiles")
    args = parser.parse_args(argv)

    if args.mtbf_only:
        print("=== MTBF Analysis (aerospace reference) ===")
        for profile in RadiationProfile:
            emu = SEUEmulator(profile)
            mtbf = emu.compute_mtbf()
            status = "PASS" if mtbf.meets_aerospace_standard else "FAIL"
            print(
                f"  {profile.value:12s}  MTBF={mtbf.mtbf_hours:,.0f} h  "
                f"SEU rate={mtbf.seu_rate_per_hour:.2e}/h  [{status}]"
            )
        return 0

    profile = RadiationProfile(args.profile)
    chip = MiliChip(use_hardware=True)

    if args.acceptance:
        report = chip.run_radiation_validation(profile=profile, log_path=str(args.log))
        print("=== Phase 5 Radiation Validation (FR-2) ===")
        print(f"  Profile:              {report.profile}")
        print(f"  SEU correction:       {report.seu_correction_pct}%  (target >= 99%)")
        print(f"  TMR latency overhead: {report.tmr_latency_overhead_pct}%  (target < 5%)")
        print(f"  TMR power overhead:   {report.tmr_power_overhead_pct}%  (target < 15%)")
        print(f"  Thermal @ 85C:        {report.thermal_degradation_85c_pct}% deg  (target <= 5%)")
        print(f"  MTBF:                 {report.mtbf_hours:,.0f} h  (target >= 10,000 h)")
        print(f"  Fault trials:         {report.total_fault_trials}")
        print(f"  SEU log:              {args.log}")
        print(f"  PASSED:               {report.passed}")
        return 0 if report.passed else 1

    validator = RadiationValidator(backend=chip.hardware_backend, profile=profile)
    correction = validator.run_fault_injection_campaign(num_trials=args.trials)
    lat_oh, pwr_oh = validator.measure_tmr_overhead()
    mtbf = SEUEmulator(profile).compute_mtbf()

    print(f"=== Fault Injection Campaign ({args.profile}) ===")
    print(f"  Trials:         {args.trials}")
    print(f"  Correction:     {correction}%")
    print(f"  TMR overhead:   {lat_oh}% latency, {pwr_oh}% power")
    print(f"  MTBF:           {mtbf.mtbf_hours:,.0f} h")
    validator.monitor.export_log(args.log)
    print(f"  Log:            {args.log}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
