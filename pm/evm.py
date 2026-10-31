"""Earned value management, schedule and RAID calculations (PMBOK formulas)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"


def load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def planned_fraction(start: date, finish: date, status: date) -> float:
    """Share of a work package planned to be done by the status date (linear over its duration)."""
    if status <= start:
        return 0.0
    if status >= finish:
        return 1.0
    return (status - start).days / (finish - start).days


@dataclass
class Evm:
    bac: float
    pv: float
    ev: float
    ac: float

    cv = property(lambda s: s.ev - s.ac)                       # cost variance
    sv = property(lambda s: s.ev - s.pv)                       # schedule variance
    cpi = property(lambda s: s.ev / s.ac if s.ac else 1.0)     # cost performance index
    spi = property(lambda s: s.ev / s.pv if s.pv else 1.0)     # schedule performance index
    eac = property(lambda s: s.bac / s.cpi)                    # estimate at completion (CPI method)
    etc = property(lambda s: s.eac - s.ac)                     # estimate to complete
    vac = property(lambda s: s.bac - s.eac)                    # variance at completion
    tcpi = property(lambda s: (s.bac - s.ev) / (s.bac - s.ac) if s.bac != s.ac else float("inf"))  # to-complete PI


def evm_for(wp: dict, status: date) -> Evm:
    fraction = planned_fraction(date.fromisoformat(wp["start"]), date.fromisoformat(wp["finish"]), status)
    return Evm(bac=wp["budget"], pv=wp["budget"] * fraction, ev=wp["budget"] * wp["complete"], ac=wp["actual"])


def programme_evm(plan: dict) -> tuple[Evm, list[tuple[dict, Evm]]]:
    status = date.fromisoformat(plan["status_date"])
    rows = [(wp, evm_for(wp, status)) for wp in plan["work_packages"]]
    total = Evm(sum(e.bac for _, e in rows), sum(e.pv for _, e in rows), sum(e.ev for _, e in rows), sum(e.ac for _, e in rows))
    return total, rows


def rag(index: float) -> str:
    """Green at 0.95 or better, amber from 0.85, red below."""
    return "Green" if index >= 0.95 else "Amber" if index >= 0.85 else "Red"


def milestone_slip(m: dict) -> int:
    """Days late against baseline (actual if achieved, otherwise forecast)."""
    reference = m["actual"] or m["forecast"]
    return (date.fromisoformat(reference) - date.fromisoformat(m["baseline"])).days


def risk_score(risk: dict) -> int:
    return risk["probability"] * risk["impact"]


def risk_rating(score: int) -> str:
    return "High" if score >= 12 else "Medium" if score >= 6 else "Low"


def velocity(sprints: list[dict], last: int = 3) -> float:
    recent = sprints[-last:]
    return sum(s["completed"] for s in recent) / len(recent)
