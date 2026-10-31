# Programme Health Dashboard

[![Tests and dashboard](https://github.com/artysficial/project-health-dashboard/actions/workflows/tests.yml/badge.svg)](https://github.com/artysficial/project-health-dashboard/actions/workflows/tests.yml)
[![Dashboard](https://img.shields.io/badge/dashboard-live-0071e3)](https://artysficial.github.io/project-health-dashboard/)

The Project Manager lens on the fictional **Arunika Bank Payment Security Modernisation** programme: a weekly
status report built from the plan, the RAID log and live delivery data.

**[View the live status report →](https://artysficial.github.io/project-health-dashboard/)**

## What it reports

- **Earned value**: PV, EV, AC, CV, SV, CPI, SPI, EAC, ETC, VAC and TCPI per work package and for the programme,
  with an S-curve of planned value, earned value and actual cost.
- **RAG status** from the worse of CPI and SPI (green ≥ 0.95, amber ≥ 0.85), capped at amber when a milestone is
  forecast late, because indices alone can look green while dates slip.
- **Milestones** with baseline, forecast and slip.
- **RAID log**: risks scored probability × impact on a heat map, issues, decisions and assumptions.
- **Velocity** of the API team from sprint data (story points from the BA backlog).
- **Live quality gate**: the latest results of the [HSM security suite](https://artysficial.github.io/hsm-api-security-lab/),
  which decide milestone M4 (security sign-off).

The hardware work package's actual cost reconciles to the committed spend in the
[procure-to-pay analytics](https://artysficial.github.io/sap-p2p-analytics/), and two open issues come straight
from the [ITGC audit](https://artysficial.github.io/itgc-audit-analytics/).

## Tests

`pytest` checks the EVM formulas against a textbook example, linear planned value and its caps, programme
roll-ups, RAG and risk-rating thresholds, milestone slip, velocity, and plan / RAID integrity.

```bash
pip install -r requirements.txt
python -m pytest && python tools/build_dashboard.py
```

Built by [Rahmadani Tyas Ningrum](https://artysficial.github.io/) · MIT licence
