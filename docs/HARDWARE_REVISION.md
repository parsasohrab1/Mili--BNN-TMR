# Hardware Silicon Revision Tracking

Mili BNN-TMR tape-out revisions are tracked in `config/chip_spec.yaml` under `tapeout.silicon_rev` and exposed through the Python API.

## Revision Timeline

| Rev | Status | Lot ID | Notes |
|-----|--------|--------|-------|
| **A0** | Current ES | `MILI-ES-A0-001` | First engineering samples (25 units) |
| **A1** | Planned | — | Metal fix + timing margin improvement |
| **B0** | Future | — | Production qualification |

## Configuration

```yaml
# config/chip_spec.yaml
tapeout:
  silicon_rev: "A0"
  lot_id: "MILI-ES-A0-001"
  foundry: "TSMC 14nm FinFET"
  packaging: "BGA-484"
  engineering_samples: 25
```

When migrating to A1, update `silicon_rev` and `lot_id`; SDK and API consumers read the active revision at runtime.

## Python API

```python
from api.python.chip_api import MiliChip
from mili_bnn_tmr.silicon_revision import SiliconRevision

chip = MiliChip()
info = chip.get_silicon_info()
# {"silicon_rev": "A0", "next_rev": "A1", "lot_id": "...", ...}

rev = SiliconRevision.from_string(chip.silicon_rev)
assert rev.next_revision() == SiliconRevision.A1
```

`MiliChip.get_status()` also reports `silicon_rev`, `packaging`, `operating_temp_c`, and `interfaces`.

## Support Tickets

Include silicon revision when contacting support:

```bash
mili-support --ticket --email you@company.com --silicon-rev A0
```

Tickets are routed to **support@mili-chip.com** with 24-hour SLA.
