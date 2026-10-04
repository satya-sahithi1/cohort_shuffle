"""
test_swapper.py — Tests for swapper.py
"""

import pytest
from backend.algorithm.swapper import optimise, _conflict_students
from backend.algorithm.scorer import pair_key, arrangement_score


class TestConflictStudents:
    def test_no_history_no_conflicts(self, empty_history):
        teams = [["A", "B"], ["C", "D"]]
        assert _conflict_students(teams, empty_history) == set()

    def test_detects_conflict(self):
        h = {pair_key("A", "B"): (1, 10)}
        teams = [["A", "B"], ["C", "D"]]
        conflict = _conflict_students(teams, h)
        assert "A" in conflict
        assert "B" in conflict
        assert "C" not in conflict

    def test_no_conflict_if_repeat_on_different_team(self):
        # A and B have history but are on different teams
        h = {pair_key("A", "B"): (1, 10)}
        teams = [["A", "C"], ["B", "D"]]
        conflict = _conflict_students(teams, h)
        assert conflict == set()


class TestOptimise:
    def test_no_history_unchanged(self, students_26, empty_history):
        import random
        from backend.algorithm.greedy import place
        rng = random.Random(42)
        teams = place(students_26, 4, empty_history, rng)
        score_before = arrangement_score(teams, empty_history)
        optimise(teams, empty_history)
        score_after = arrangement_score(teams, empty_history)
        assert score_before == score_after == 0

    def test_improves_or_stays_same(self):
        # Force a bad arrangement: known repeat pairs on same team
        h = {
            pair_key("A", "B"): (1, 10),
            pair_key("C", "D"): (1, 10),
        }
        # Bad: A+B on team1, C+D on team2
        # Better: A+C on team1, B+D on team2 (strangers paired)
        teams = [["A", "B", "E"], ["C", "D", "F"]]
        score_before = arrangement_score(teams, h)
        optimise(teams, h)
        score_after = arrangement_score(teams, h)
        assert score_after <= score_before

    def test_all_students_still_present(self, students_26, small_history):
        import random
        from backend.algorithm.greedy import place
        rng = random.Random(42)
        teams = place(students_26, 5, small_history, rng)
        before = sorted(s for t in teams for s in t)
        optimise(teams, small_history)
        after = sorted(s for t in teams for s in t)
        assert before == after

    def test_single_team_no_crash(self, empty_history):
        teams = [["A", "B", "C"]]
        optimise(teams, empty_history)  # should not raise
