"""
test_greedy.py — Tests for greedy.py
"""

import random
import pytest
from algorithm.greedy import place
from algorithm.scorer import pair_key


RNG = random.Random(42)


def fresh_rng():
    return random.Random(42)


class TestTeamSizes:
    def test_exact_division(self, students_26, empty_history):
        # 26 students, team size 2 → 13 teams of 2
        teams = place(students_26, 2, empty_history, fresh_rng())
        assert len(teams) == 13
        assert all(len(t) == 2 for t in teams)

    def test_absorb_remainder(self, empty_history):
        # 13 students, team size 4 → r=1, always absorb → 3 teams
        students = [f"s{i}" for i in range(13)]
        teams = place(students, 4, empty_history, fresh_rng())
        sizes = sorted(len(t) for t in teams)
        assert sum(sizes) == 13
        assert len(teams) == 3
        assert all(len(t) > 1 for t in teams)  # no solo teams

    def test_new_small_team_for_large_remainder(self, empty_history):
        # 15 students, team size 4 → r=3 > 4/2=2 → new small team → 4 teams
        students = [f"s{i}" for i in range(15)]
        teams = place(students, 4, empty_history, fresh_rng())
        assert len(teams) == 4
        assert sum(len(t) for t in teams) == 15

    def test_no_solo_team(self, empty_history):
        # r==1 must always absorb, never produce a team of 1
        students = [f"s{i}" for i in range(13)]  # 13 % 4 = 1
        teams = place(students, 4, empty_history, fresh_rng())
        assert all(len(t) > 1 for t in teams)

    def test_fewer_than_team_size(self, empty_history):
        students = ["A", "B", "C"]
        teams = place(students, 6, empty_history, fresh_rng())
        assert len(teams) == 1
        assert set(teams[0]) == {"A", "B", "C"}

    def test_empty_students(self, empty_history):
        teams = place([], 4, empty_history, fresh_rng())
        assert teams == []


class TestAllStudentsPlaced:
    def test_all_placed_no_history(self, students_62, empty_history):
        teams = place(students_62, 6, empty_history, fresh_rng())
        placed = [s for t in teams for s in t]
        assert sorted(placed) == sorted(students_62)

    def test_all_placed_with_history(self, students_26, small_history):
        teams = place(students_26, 4, small_history, fresh_rng())
        placed = [s for t in teams for s in t]
        assert sorted(placed) == sorted(students_26)

    def test_no_duplicates(self, students_62, empty_history):
        teams = place(students_62, 5, empty_history, fresh_rng())
        placed = [s for t in teams for s in t]
        assert len(placed) == len(set(placed))


class TestConflictedStudentsPlacedWell:
    def test_prefers_strangers(self):
        # A has history with B and C but not D, E, F
        h = {
            pair_key("A", "B"): (1, 10),
            pair_key("A", "C"): (1, 10),
        }
        students = ["A", "B", "C", "D", "E", "F"]
        # Run many times — A should almost always end up with D, E, or F
        times_with_stranger = 0
        for seed in range(50):
            rng = random.Random(seed)
            teams = place(students, 3, h, rng)
            for team in teams:
                if "A" in team:
                    if any(s in ("D", "E", "F") for s in team):
                        times_with_stranger += 1
        assert times_with_stranger >= 40  # ≥ 80% of runs
