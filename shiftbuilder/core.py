"""Build a fair roster. The rules are never broken: if a shift cannot be filled, the roster says so
and explains why, because a hidden gap on a real rota is worse than a visible one."""
import math
import random
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class Person:
    name: str
    skills: tuple = ()
    max_shifts: int = 5
    unavailable: tuple = ()      # days, or (day, shift name) pairs
    prefers_off: tuple = ()      # days they would rather not work


@dataclass
class Shift:
    day: int
    name: str
    needs: dict                  # {skill: how many}. Use "any" for no skill
    start: int = 8
    hours: int = 8
    night: bool = False


def key(s):
    return (s.day, s.name)


def conflicts(person_shifts, s, min_rest=11):
    """True if a person on these shifts cannot also take shift s: same day, or too little rest."""
    a = s.day * 24 + s.start
    for o in person_shifts:
        if o.day == s.day:
            return True
        b = o.day * 24 + o.start
        if a >= b:
            gap = a - (b + o.hours)
        else:
            gap = b - (a + s.hours)
        if gap < min_rest:
            return True
    return False


def can_work(p, s, role):
    if s.day in p.unavailable or (s.day, s.name) in p.unavailable:
        return False
    return role == "any" or role in p.skills


def violations(people, shifts, roster, min_rest=11):
    """An independent check. roster: {(day, shift name): [(person, role), ...]}."""
    by_name = {p.name: p for p in people}
    by_key = {key(s): s for s in shifts}
    out = []
    worked = defaultdict(list)
    for k, staff in roster.items():
        s = by_key[k]
        seen = set()
        for name, role in staff:
            p = by_name[name]
            if name in seen:
                out.append(f"{name} is listed twice on {k}")
            seen.add(name)
            if not can_work(p, s, role):
                out.append(f"{name} cannot work {k} as {role}")
            worked[name].append(s)
    for name, list_ in worked.items():
        if len(list_) > by_name[name].max_shifts:
            out.append(f"{name} has {len(list_)} shifts, limit {by_name[name].max_shifts}")
        ordered = sorted(list_, key=lambda s: s.day * 24 + s.start)
        for i, a in enumerate(ordered):
            if conflicts(ordered[:i] + ordered[i + 1:], a, min_rest):
                out.append(f"{name} has too little rest around {key(a)}")
                break
    return out


def unfilled(shifts, roster):
    out = []
    for s in shifts:
        have = defaultdict(int)
        for _, role in roster.get(key(s), []):
            have[role] += 1
        for role, n in s.needs.items():
            if have[role] < n:
                out.append((s, role, n - have[role]))
    return out


def cost(people, shifts, roster):
    """Lower is better: uneven load, uneven nights, and days people asked to have off."""
    by_key = {key(s): s for s in shifts}
    load, nights, prefer = defaultdict(int), defaultdict(int), 0
    by_name = {p.name: p for p in people}
    for k, staff in roster.items():
        for name, _ in staff:
            load[name] += 1
            nights[name] += by_key[k].night
            if by_key[k].day in by_name[name].prefers_off:
                prefer += 1
    def spread(d):
        v = [d[p.name] for p in people]
        m = sum(v) / len(v)
        return sum((x - m) ** 2 for x in v)
    return 3 * spread(load) + 5 * spread(nights) + 4 * prefer


def build(people, shifts, seed=0, steps=20000, min_rest=11):
    """Greedy fill of the hardest places first, then annealing with moves that keep every rule."""
    rng = random.Random(seed)
    roster = {key(s): [] for s in shifts}
    worked = {p.name: [] for p in people}
    places = [(s, role) for s in shifts for role, n in s.needs.items() for _ in range(n)]

    def options(s, role):
        return [p for p in people if len(worked[p.name]) < p.max_shifts and can_work(p, s, role) and not conflicts(worked[p.name], s, min_rest) and all(p.name != n for n, _ in roster[key(s)])]
    remaining = list(places)
    while remaining:
        remaining.sort(key=lambda t: len(options(*t)))
        s, role = remaining.pop(0)
        opts = options(s, role)
        if not opts:
            continue
        rng.shuffle(opts)
        p = min(opts, key=lambda x: (len(worked[x.name]) / max(x.max_shifts, 1), s.day in x.prefers_off, len(x.skills)))
        roster[key(s)].append((p.name, role))
        worked[p.name].append(s)
    by_key = {key(s): s for s in shifts}
    by_name = {p.name: p for p in people}
    current = cost(people, shifts, roster)
    filled = [k for k in roster if roster[k]]
    for i in range(steps if filled else 0):
        temp = 3.0 * (1 - i / steps) + 1e-3
        k = rng.choice(filled)
        if not roster[k]:
            continue
        idx = rng.randrange(len(roster[k]))
        name, role = roster[k][idx]
        s = by_key[k]
        other = rng.choice(people)
        if other.name == name or any(other.name == n for n, _ in roster[k]) or not can_work(other, s, role) or len(worked[other.name]) >= other.max_shifts:
            continue
        if conflicts(worked[other.name], s, min_rest):
            continue
        roster[k][idx] = (other.name, role)
        worked[name].remove(s)
        worked[other.name].append(s)
        new = cost(people, shifts, roster)
        if new <= current or rng.random() < math.exp((current - new) / temp):
            current = new
        else:
            roster[k][idx] = (name, role)
            worked[other.name].remove(s)
            worked[name].append(s)
    return roster


def explain(people, s, role, roster, shifts, min_rest=11):
    """Why a place could not be filled, in words a manager can act on."""
    worked = defaultdict(list)
    by_key = {key(x): x for x in shifts}
    for k, staff in roster.items():
        for name, _ in staff:
            worked[name].append(by_key[k])
    counts = defaultdict(int)
    for p in people:
        if role != "any" and role not in p.skills:
            counts["lack the skill"] += 1
        elif not can_work(p, s, role):
            counts["are unavailable"] += 1
        elif any(n == p.name for n, _ in roster.get(key(s), [])):
            counts["are already on this shift"] += 1
        elif len(worked[p.name]) >= p.max_shifts:
            counts["have reached their shift limit"] += 1
        elif conflicts(worked[p.name], s, min_rest):
            counts["need rest"] += 1
    return ", ".join(f"{n} {why}" for why, n in sorted(counts.items()))


def fairness(people, shifts, roster):
    by_key = {key(s): s for s in shifts}
    out = {p.name: {"shifts": 0, "nights": 0, "hours": 0} for p in people}
    for k, staff in roster.items():
        for name, _ in staff:
            out[name]["shifts"] += 1
            out[name]["nights"] += by_key[k].night
            out[name]["hours"] += by_key[k].hours
    return out


def load(data):
    people = [Person(p["name"], tuple(p.get("skills", ())), p.get("max_shifts", 5), tuple(tuple(u) if isinstance(u, list) else u for u in p.get("unavailable", ())), tuple(p.get("prefers_off", ()))) for p in data["people"]]
    shifts = [Shift(d, t["name"], t["needs"], t.get("start", 8), t.get("hours", 8), t.get("night", False)) for d in range(data.get("days", 7)) for t in data["shifts"]]
    return people, shifts


EXAMPLE = {"days": 7, "people": [{"name": f"Nurse {i}", "skills": ["nurse"], "max_shifts": 5} for i in range(1, 6)] + [{"name": f"Helper {i}", "skills": ["helper"], "max_shifts": 5, "prefers_off": [4]} for i in range(1, 5)],
           "shifts": [{"name": "Day", "start": 8, "hours": 8, "needs": {"nurse": 1, "helper": 1}}, {"name": "Night", "start": 22, "hours": 8, "night": True, "needs": {"nurse": 1}}]}
