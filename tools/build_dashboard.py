"""Builds the programme status dashboard (site/index.html)."""

import json
import sys
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import report_kit as rk  # noqa: E402
from pm.evm import load, milestone_slip, planned_fraction, programme_evm, rag, risk_rating, risk_score, velocity  # noqa: E402

HSM_RESULTS = "https://artysficial.github.io/hsm-api-security-lab/results.json"


def quality_gate() -> tuple[str, str, str]:
    """Live security test status from the SDET project (the M4 sign-off gate)."""
    try:
        with urllib.request.urlopen(HSM_RESULTS, timeout=15) as response:
            counts = json.loads(response.read())["counts"]
        passed, defects = counts.get("passed", 0), counts.get("known defect", 0)
        failed = counts.get("failed", 0) + counts.get("error", 0)
        tone = "bad" if failed else "warn" if defects else "ok"
        return f"{passed}/{passed + defects + failed}", f"{defects} open findings, {failed} failures (live)", tone
    except Exception:
        return "n/a", "security results unavailable", "warn"


def main() -> None:
    plan, raid = load("plan.json"), load("raid.json")
    status = date.fromisoformat(plan["status_date"])
    total, rows = programme_evm(plan)
    gate_value, gate_note, gate_tone = quality_gate()
    tone = lambda colour: {"Green": "ok", "Amber": "warn", "Red": "bad"}[colour]
    late = [m for m in plan["milestones"] if not m["actual"] and milestone_slip(m) > 0]

    body = rk.kpis([
        ("Cost performance (CPI)", f"{total.cpi:.2f}", f"CV Rp {total.cv:,.0f} m", tone(rag(total.cpi))),
        ("Schedule performance (SPI)", f"{total.spi:.2f}", f"SV Rp {total.sv:,.0f} m", tone(rag(total.spi))),
        ("Estimate at completion", f"Rp {total.eac / 1000:,.1f} bn", f"budget Rp {total.bac / 1000:,.1f} bn · VAC Rp {total.vac:,.0f} m", "ok" if total.vac >= 0 else "bad"),
        ("Complete", f"{total.ev / total.bac:.0%}", f"planned {total.pv / total.bac:.0%} by {status:%d %b %Y}"),
        ("Milestones at risk", len(late), "forecast later than baseline", "warn" if late else "ok"),
        ("Security tests", gate_value, gate_note, gate_tone),
    ])

    months = [h["month"] for h in plan["history"]] + [plan["status_date"][:7]]
    ev = [h["ev"] / 1000 for h in plan["history"]] + [total.ev / 1000]
    ac = [h["ac"] / 1000 for h in plan["history"]] + [total.ac / 1000]
    pv = []
    for month in months:
        y, m = map(int, month.split("-"))
        month_end = date(y + (m == 12), m % 12 + 1, 1)
        month_end = min(month_end, status)
        pv.append(sum(wp["budget"] * planned_fraction(date.fromisoformat(wp["start"]), date.fromisoformat(wp["finish"]), month_end) for wp in plan["work_packages"]) / 1000)
    body += rk.section("S-curve: planned, earned and actual (IDR bn, cumulative)", rk.lines(
        [("Planned value", [round(v, 1) for v in pv], "var(--line)"), ("Earned value", [round(v, 1) for v in ev], "var(--blue)"), ("Actual cost", [round(v, 1) for v in ac], "var(--orange)")],
        [m[2:] for m in months]))

    wp_rows = [[wp["id"], wp["name"], wp["owner"], f"{wp['complete']:.0%}", f"{e.pv:,.0f}", f"{e.ev:,.0f}", f"{e.ac:,.0f}", f"{e.cpi:.2f}", f"{e.spi:.2f}", rk.pill(rag(min(e.cpi, e.spi)))] for wp, e in rows]
    body += rk.section("Work packages (IDR m)", rk.table(["WP", "Work package", "Owner", "Done", "PV", "EV", "AC", "CPI", "SPI", "RAG"], wp_rows, {9}),
                       "RAG uses the worse of CPI and SPI. WP2's actual cost reconciles to committed spend in the procure-to-pay analytics.")

    ms_rows = [[m["id"], m["name"], m["baseline"], m["actual"] or m["forecast"], f"{milestone_slip(m):+d} d", rk.pill("Complete" if m["actual"] else ("At risk" if milestone_slip(m) > 0 else "On track"))] for m in plan["milestones"]]
    body += rk.section("Milestones", rk.table(["ID", "Milestone", "Baseline", "Actual / forecast", "Slip", "Status"], ms_rows, {5}))

    open_risks = [r for r in raid["risks"] if r["status"] == "Open"]
    heat = Counter((r["probability"], r["impact"]) for r in open_risks)
    cells = ""
    for p in range(5, 0, -1):
        cells += f'<tr><th style="text-align:right">P{p}</th>'
        for i in range(1, 6):
            score = p * i
            colour = "var(--bad-bg)" if score >= 12 else "var(--warn-bg)" if score >= 6 else "var(--ok-bg)"
            ids = ", ".join(r["id"] for r in open_risks if (r["probability"], r["impact"]) == (p, i))
            cells += f'<td style="background:{colour};text-align:center;height:46px;border-radius:8px;font-weight:600">{rk.esc(ids)}</td>'
        cells += "</tr>"
    heatmap = f'<table style="border-spacing:4px;border-collapse:separate">{cells}<tr><th></th>{"".join(f"<th style=text-align:center>I{i}</th>" for i in range(1, 6))}</tr></table>'
    sprint_bars = rk.bars([(f"Sprint {s['sprint']}", s["completed"]) for s in plan["sprints"]], unit=" pts")
    body += rk.grid(
        rk.section("Risk heat map (open risks)", heatmap, "Probability × impact. Red cells score 12 or more."),
        rk.section(f"API team velocity · {velocity(plan['sprints']):.1f} pts/sprint", sprint_bars, "Completed story points per sprint (stories from the BA backlog)."),
    )
    risk_rows = [[r["id"], r["title"], f"{r['probability']}×{r['impact']}={risk_score(r)}", rk.pill(risk_rating(risk_score(r))), r["owner"], r["response"]] for r in sorted(open_risks, key=lambda r: -risk_score(r))]
    body += rk.section("RAID: risks", rk.table(["ID", "Risk", "Score", "Rating", "Owner", "Response"], risk_rows, {3}))
    body += rk.section("RAID: issues, decisions and assumptions", rk.table(["ID", "Item", "Owner / by", "Detail"],
        [[i["id"], i["title"], i["owner"], f"{i['severity']} · {i['action']} by {i['due']}"] for i in raid["issues"]]
        + [[d["id"], d["decision"], d["by"], f"Decision {d['date']}"] for d in raid["decisions"]]
        + [[a["id"], a["assumption"], "PMO", a["status"]] for a in raid["assumptions"]]))
    checks = json.loads((ROOT / "reports" / "results.json").read_text(encoding="utf-8"))
    body += rk.section("Calculation checks", rk.table(["Check", "Area", "Result"], [[c["title"], c["category"], rk.pill(c["status"])] for c in checks["tests"]], {2}))

    # indices alone can look green while milestones slip: a forecast-late milestone caps the status at amber
    overall = rag(min(total.cpi, total.spi))
    if late and overall == "Green":
        overall = "Amber"
    budget = "on budget" if total.vac >= 0 else "over budget"
    verdict = (f"Overall {overall}: {budget}, {len(late)} milestone{'s' if len(late) != 1 else ''} forecast late", tone(overall))
    rk.write(str(ROOT / "site" / "index.html"), rk.page(
        title="Programme Health",
        eyebrow="Project Manager · Status report",
        summary=f"Status of the {plan['programme']} programme at {status:%d %B %Y}: earned value, milestones, RAID log, delivery velocity and the live security quality gate.",
        body=body, repo="project-health-dashboard", verdict=verdict,
    ))
    print(f"dashboard built: CPI {total.cpi:.2f} SPI {total.spi:.2f}")


if __name__ == "__main__":
    main()
