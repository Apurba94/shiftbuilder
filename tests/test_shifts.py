import json
import random
import unittest

from shiftbuilder import core, create_app
from shiftbuilder.core import EXAMPLE, Person, Shift, build, conflicts, cost, explain, fairness, key, load, unfilled, violations


def night(d):
    return Shift(d, "Night", {"any": 1}, 22, 8, True)


def morning(d):
    return Shift(d, "Morning", {"any": 1}, 6, 8)


class TestRest(unittest.TestCase):
    def test_same_day(self):
        self.assertTrue(conflicts([morning(0)], Shift(0, "Eve", {}, 16, 6)))

    def test_night_then_morning_is_refused(self):
        self.assertTrue(conflicts([night(0)], morning(1)))

    def test_enough_rest_is_fine(self):
        self.assertFalse(conflicts([night(0)], night(1)))
        self.assertFalse(conflicts([morning(0)], morning(1)))

    def test_order_of_shifts_does_not_matter(self):
        self.assertTrue(conflicts([morning(1)], night(0)))


class TestChecker(unittest.TestCase):
    def test_finds_each_break(self):
        a = Person("A", ("nurse",), 1, unavailable=(2,))
        s = [Shift(0, "D", {"nurse": 1}), Shift(1, "D", {"nurse": 1}), Shift(2, "D", {"nurse": 1})]
        v = violations([a], s, {(0, "D"): [("A", "nurse")], (1, "D"): [("A", "nurse")]})
        self.assertTrue(any("limit 1" in x for x in v))
        v = violations([a], s, {(2, "D"): [("A", "nurse")]})
        self.assertTrue(any("cannot work" in x for x in v))
        v = violations([Person("B", ())], s, {(0, "D"): [("B", "nurse")]})
        self.assertTrue(any("cannot work" in x for x in v))
        v = violations([Person("A")], [night(0), morning(1)], {(0, "Night"): [("A", "any")], (1, "Morning"): [("A", "any")]})
        self.assertTrue(any("rest" in x for x in v))


class TestBuild(unittest.TestCase):
    def test_example_is_clean_and_full(self):
        people, shifts = load(EXAMPLE)
        r = build(people, shifts, 1, 3000)
        self.assertEqual(violations(people, shifts, r), [])
        self.assertEqual(unfilled(shifts, r), [])

    def test_random_teams_never_break_a_rule(self):
        rng = random.Random(1)
        for seed in range(25):
            skills = ["a", "b", "c"]
            people = [Person(f"P{i}", tuple(rng.sample(skills, rng.randint(1, 3))), rng.randint(2, 6), tuple(rng.sample(range(7), rng.randint(0, 2)))) for i in range(rng.randint(3, 12))]
            shifts = [Shift(d, n, {rng.choice(skills): rng.randint(1, 2)}, st, 8, st == 22) for d in range(7) for n, st in (("M", 6), ("E", 14), ("N", 22))]
            r = build(people, shifts, seed, 800)
            self.assertEqual(violations(people, shifts, r), [], seed)

    def test_annealing_makes_it_fairer(self):
        people, shifts = load(EXAMPLE)
        self.assertLessEqual(cost(people, shifts, build(people, shifts, 2, 4000)), cost(people, shifts, build(people, shifts, 2, 0)))

    def test_nights_are_shared(self):
        people, shifts = load(EXAMPLE)
        f = fairness(people, shifts, build(people, shifts, 3, 6000))
        nights = [v["nights"] for k, v in f.items() if k.startswith("Nurse")]
        self.assertLessEqual(max(nights) - min(nights), 1)

    def test_preferences_are_honoured_when_possible(self):
        people = [Person("A", prefers_off=(0,)), Person("B", prefers_off=(1,))]
        shifts = [Shift(0, "D", {"any": 1}), Shift(1, "D", {"any": 1})]
        r = build(people, shifts, 1, 500)
        self.assertEqual(r[(0, "D")], [("B", "any")])

    def test_same_seed_same_roster(self):
        people, shifts = load(EXAMPLE)
        self.assertEqual(build(people, shifts, 5, 1000), build(people, shifts, 5, 1000))


class TestGaps(unittest.TestCase):
    def test_a_gap_is_shown_never_hidden(self):
        people = [Person("A", ("nurse",), 2)]
        shifts = [Shift(d, "D", {"nurse": 1}) for d in range(4)]
        r = build(people, shifts, 1, 100)
        self.assertEqual(violations(people, shifts, r), [])
        self.assertEqual(sum(g[2] for g in unfilled(shifts, r)), 2)

    def test_explanations(self):
        p = [Person("A", ("nurse",), 1), Person("B", ("cook",)), Person("C", ("nurse",), unavailable=(1,))]
        s = [Shift(0, "D", {"nurse": 1}), Shift(1, "D", {"nurse": 1})]
        r = {(0, "D"): [("A", "nurse")], (1, "D"): []}
        text = explain(p, s[1], "nurse", r, s)
        self.assertIn("1 lack the skill", text)
        self.assertIn("1 are unavailable", text)
        self.assertIn("1 have reached their shift limit", text)

    def test_unavailable_shift_pairs(self):
        p = Person("A", (), 5, unavailable=((0, "Night"),))
        self.assertFalse(core.can_work(p, night(0), "any"))
        self.assertTrue(core.can_work(p, night(1), "any"))


class TestApp(unittest.TestCase):
    def setUp(self):
        self.a = create_app()

    def test_flow(self):
        page = self.a.post("/", input=json.dumps(EXAMPLE), seed=1).body.decode()
        self.assertIn("Every place is filled", page)
        self.assertIn("Nurse 1", page)

    def test_gaps_are_explained(self):
        data = {"days": 3, "people": [{"name": "A", "skills": ["n"], "max_shifts": 1}], "shifts": [{"name": "D", "needs": {"n": 1}}]}
        page = self.a.post("/", input=json.dumps(data), seed=1).body.decode()
        self.assertIn("reached their shift limit", page)

    def test_bad_input(self):
        self.assertEqual(self.a.post("/", input="{bad").status, 400)
        self.assertEqual(self.a.post("/", input='{"people": [], "shifts": []}').status, 400)


if __name__ == "__main__":
    unittest.main()
