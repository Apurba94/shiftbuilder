# ShiftBuilder

Build a fair weekly roster for a clinic, a help desk or a team of volunteers. Nobody works two shifts in a day, nobody goes from a night shift straight into a morning, and the hard shifts are shared.

```
python -m shiftbuilder
```

Then open http://127.0.0.1:8037. A worked example is ready to edit. It needs Python 3.10 or newer.

## What it handles

**Rules that are never broken:** skills for each role, days people cannot work, a limit on shifts, one shift a day, and at least 11 hours of rest between shifts.

**Goals it works towards:** an even share of shifts, an even share of nights, and days people asked to have off.

## How it works

The hardest places to fill go first, then simulated annealing swaps people to improve fairness. Each swap keeps every rule true.

**A gap is always shown.** If a shift cannot be filled, the roster says so, with reasons such as "2 lack the skill, 1 has reached their shift limit". An independent checker then re-tests the roster, and it shares no code with the builder's own bookkeeping.

## How it is tested

Random teams and shift patterns are built, and every roster must pass the independent checker. Rest rules are tested in both directions, tests confirm that nights are shared within one shift, and short-staffed cases must show their gaps rather than break a rule.

## Limits

The search is heuristic, so a roster with gaps does not prove that no full roster exists. Try other seeds. Labour law and agency rules differ from place to place, and the 11-hour default is only a default. Please check the result with the people affected. The input is JSON, and rosters are not saved between runs.

## Tests

```
python -m unittest discover -s tests
```

MIT licence.
