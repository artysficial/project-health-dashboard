"""EVM formulas, RAG rules and plan integrity."""

from datetime import date

import pytest

from pm.evm import Evm, milestone_slip, planned_fraction, programme_evm, rag, risk_rating, risk_score, velocity


@pytest.mark.category("EVM formulas")
@pytest.mark.severity("critical")
def test_textbook_example():
    """BAC 100, PV 50, EV 40, AC 50 gives CPI 0.8, SPI 0.8, EAC 125, VAC -25"""
    e = Evm(bac=100, pv=50, ev=40, ac=50)
    assert (e.cv, e.sv) == (-10, -10)
    assert e.cpi == pytest.approx(0.8) and e.spi == pytest.approx(0.8)
    assert e.eac == pytest.approx(125) and e.vac == pytest.approx(-25) and e.etc == pytest.approx(75)
    assert e.tcpi == pytest.approx(60 / 50)


@pytest.mark.category("EVM formulas")
@pytest.mark.severity("high")
@pytest.mark.parametrize("status, expected", [("2026-01-01", 0.0), ("2026-01-11", 0.5), ("2026-01-21", 1.0), ("2026-03-01", 1.0)])
def test_planned_value_is_linear_over_the_duration(status, expected):
    """Planned share grows linearly between start and finish and is capped at 0 and 1"""
    assert planned_fraction(date(2026, 1, 1), date(2026, 1, 21), date.fromisoformat(status)) == pytest.approx(expected)


@pytest.mark.category("EVM formulas")
@pytest.mark.severity("high")
def test_programme_totals_equal_the_sum_of_work_packages(plan):
    """Programme BAC, PV, EV and AC are the sums of the work packages"""
    total, rows = programme_evm(plan)
    for field in ("bac", "pv", "ev", "ac"):
        assert getattr(total, field) == pytest.approx(sum(getattr(e, field) for _, e in rows))


@pytest.mark.category("Status rules")
@pytest.mark.severity("medium")
@pytest.mark.parametrize("index, colour", [(1.02, "Green"), (0.95, "Green"), (0.949, "Amber"), (0.85, "Amber"), (0.849, "Red")])
def test_rag_thresholds(index, colour):
    """RAG: green from 0.95, amber from 0.85, red below"""
    assert rag(index) == colour


@pytest.mark.category("Status rules")
@pytest.mark.severity("medium")
@pytest.mark.parametrize("p, i, rating", [(3, 4, "High"), (2, 3, "Medium"), (1, 4, "Low"), (5, 5, "High")])
def test_risk_rating_from_probability_and_impact(p, i, rating):
    """Risk score is probability x impact: 12+ high, 6+ medium"""
    assert risk_rating(risk_score({"probability": p, "impact": i})) == rating


@pytest.mark.category("Status rules")
@pytest.mark.severity("low")
def test_milestone_slip_uses_actual_when_achieved():
    """Slip is measured on the actual date once achieved, otherwise on the forecast"""
    assert milestone_slip({"baseline": "2026-07-31", "forecast": "2026-07-31", "actual": "2026-08-07"}) == 7
    assert milestone_slip({"baseline": "2026-10-30", "forecast": "2026-11-20", "actual": ""}) == 21


@pytest.mark.category("Status rules")
@pytest.mark.severity("low")
def test_velocity_is_the_recent_average(plan):
    """Velocity is the average completed points of the last three sprints"""
    assert velocity([{"completed": n} for n in (8, 13, 13, 8, 3)]) == pytest.approx(8)


@pytest.mark.category("Plan integrity")
@pytest.mark.severity("high")
def test_work_packages_are_well_formed(plan):
    """Every work package finishes after it starts, has a budget and a completion between 0 and 1"""
    for wp in plan["work_packages"]:
        assert wp["finish"] > wp["start"] and wp["budget"] > 0 and 0 <= wp["complete"] <= 1 and wp["actual"] >= 0


@pytest.mark.category("Plan integrity")
@pytest.mark.severity("medium")
def test_history_is_cumulative(plan):
    """Monthly earned value and actual cost never decrease"""
    for field in ("ev", "ac"):
        values = [h[field] for h in plan["history"]]
        assert values == sorted(values)


@pytest.mark.category("Plan integrity")
@pytest.mark.severity("medium")
def test_every_open_risk_has_an_owner_and_response(raid):
    """Open risks are owned and have a response"""
    for risk in raid["risks"]:
        if risk["status"] == "Open":
            assert risk["owner"] and risk["response"]
            assert 1 <= risk["probability"] <= 5 and 1 <= risk["impact"] <= 5
