# Phase 7 — Customer Release Guide

## Overview

Phase 7 delivers the production-ready **Mili BNN-TMR SDK v1.0** for customer deployment,
including production QC, certification tracking, and automated release validation.

## Deliverables

| Item | Path |
|------|------|
| SDK package | `dist/mili-bnn-tmr-sdk-1.0.0.tar.gz` |
| Production QC | `production/qc_checklist.yaml` |
| Certifications | `release/certifications/` |
| Datasheet | `docs/DATASHEET.md` |
| Integration Guide | `docs/INTEGRATION.md` |
| API Reference | `docs/API_REFERENCE.md` |
| Release notes | `release/RELEASE_NOTES_v1.0.md` |
| Quick-start | `examples/quickstart_classify.py` |

## Acceptance Criteria

| Metric | Target | Command |
|--------|--------|---------|
| Benchmark compliance | > 90% | `mili-release --acceptance` |
| Test coverage | > 90% | `pytest` + coverage report |
| SDK delivery | < 7 days | `chip_spec.yaml` → `sdk_delivery_days: 5` |

## Quick Start

```bash
pip install -e ".[dev,ml]"

# Build and validate release
mili-release --acceptance

# Build SDK only
mili-release --build-sdk -o dist/

# Production QC report
mili-release --qc

# List certifications
mili-release --certs
```

## SDK Package Contents

Built by `SDKPackager`:

- `drivers/` — Linux RT, Zephyr, FreeRTOS
- `api/python/` — Python host API
- `api/cpp/` — C/C++ headers
- `src/mili_bnn_tmr/compiler/` — mili-compile
- `src/mili_bnn_tmr/benchmark/` — mili-benchmark
- `docs/` — Datasheet, Integration, API Reference
- `config/chip_spec.yaml` — Measured silicon parameters
- `examples/` — Quick-start scripts

## Production QC Flow

```
Wafer CP → BGA Assembly → Final Test → Burn-in → Ship
```

Each stage defined in `production/qc_checklist.yaml`.

## Certifications

| Standard | Status |
|----------|--------|
| ECSS-Q-ST-60-15C | Certified |
| DO-254 (DAL-B) | In progress |

## Customer Onboarding

1. Customer receives BGA-484 hardware (engineering or production lot)
2. SDK delivered within 5 business days (`sdk_delivery_days`)
3. Run `examples/quickstart_classify.py`
4. Follow `docs/INTEGRATION.md` for host wiring
5. Contact support@mili-chip.com for integration assistance

## CI Gate

```yaml
- mili-release --acceptance
- pytest tests/test_release.py
```
