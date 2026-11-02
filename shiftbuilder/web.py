"""The offline web app: paste the team and shifts as JSON, and read the roster."""
import json

from . import core
from .fieldkit import App, Fail, card, form, h, stats, table

DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


def create_app(db=":memory:"):
    a = App("ShiftBuilder", db, "", [("Build a roster", "/")])

    @a.route("/", ("GET", "POST"))
    def home(req):
        if req.method == "GET":
            return a.page("Build a roster", card("Team and shifts as JSON", form(a, "/", [("input", "Input", "textarea", json.dumps(core.EXAMPLE, indent=1)), ("seed", "Seed", "number", 1)], "Build")))
        try:
            people, shifts = core.load(json.loads(req.text("input", limit=500000)))
        except (ValueError, KeyError, TypeError) as exc:
            raise Fail(f"Could not read that: {exc}") from None
        if not people or not shifts:
            raise Fail("Add at least one person and one shift")
        roster = core.build(people, shifts, int(req.number("seed", 0)), 6000)
        broken = core.violations(people, shifts, roster)
        if broken:
            raise Fail("Internal check failed: " + "; ".join(broken[:3]), 500)
        gaps = core.unfilled(shifts, roster)
        names = sorted({s.name for s in shifts}, key=lambda n: min(s.start for s in shifts if s.name == n))
        days = sorted({s.day for s in shifts})
        rows = [{"s": n, "c": [", ".join(f"{p}" for p, _ in roster.get((d, n), [])) for d in days]} for n in names]
        cols = [("Shift", "s")] + [(DAYS[d % 7], (lambda i: lambda r: r["c"][i])(i)) for i, d in enumerate(days)]
        fair = core.fairness(people, shifts, roster)
        body = stats([("Shifts", len(shifts)), ("Places unfilled", sum(g[2] for g in gaps)), ("Rule breaks", 0)])
        body += card("Roster", table(rows, cols))
        body += card("Unfilled places", table(gaps, [("Day", lambda g: DAYS[g[0].day % 7]), ("Shift", lambda g: g[0].name), ("Role", lambda g: g[1]), ("Short by", lambda g: g[2]), ("Why", lambda g: core.explain(people, g[0], g[1], roster, shifts))], "Every place is filled."))
        body += card("Fairness", table(list(fair.items()), [("Person", lambda r: r[0]), ("Shifts", lambda r: r[1]["shifts"]), ("Nights", lambda r: r[1]["nights"]), ("Hours", lambda r: r[1]["hours"])]))
        return a.page("Roster", body)

    return a
