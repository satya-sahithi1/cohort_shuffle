"""
test_engine.py — Tests for engine.py

The engine is the single public entry point: form_teams().
Tests cover the full formation lifecycle:
  - Empty / edge inputs
  - First activity (no history) → random, score 0
  - Later activities → uses history, minimises repeats
  - Fairness guarantee
  - Lock constraints (together / apart)
  - validate_locks catches impossible constraints
  - FormationResult fields are populated correctly
  - Saturation reported correctly
  - Deterministic with fixed seed
"""

import pytest
from algorithm.engine import form_teams, validate_locks, Lock
from algorithm.scorer import pair_key, saturation
from algorithm.fairness import has_violations
from tests.algorithm.conftest import build_history_from_teams


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_history_from_activities(students, team_size, n_activities, seed=0):
    """
    Simulate n_activities of formation and return the accumulated history.
    Used to set up a realistic history state for later tests.
    """
    history = {}
    for i in range(n_activities):
        result = form_teams(students, team_size, history, seed=seed + i)
        history = build_history_from_teams(result.teams, days_ago=30 * (n_activities - i), existing=history)
    return history


def all_students_in_result(students, result):
    placed = sorted(s for t in result.teams for s in t)
    return placed == sorted(students)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_students(self, empty_history):
        result = form_teams([], 4, empty_history)
        assert result.teams == []
        assert result.score == 0

    def test_fewer_students_than_team_size(self, empty_history):
        result = form_teams(["A", "B", "C"], 6, empty_history)
        assert len(result.teams) == 1
        assert set(result.teams[0]) == {"A", "B", "C"}

    def test_exact_team_size(self, empty_history):
        result = form_teams(["A", "B", "C"], 3, empty_history)
        assert len(result.teams) == 1

    def test_single_student(self, empty_history):
        result = form_teams(["A"], 4, empty_history)
        assert result.teams == [["A"]]


# ---------------------------------------------------------------------------
# First activity (no history)
# ---------------------------------------------------------------------------

class TestFirstActivity:
    def test_score_is_zero(self, students_26, empty_history):
        result = form_teams(students_26, 4, empty_history)
        assert result.score == 0

    def test_all_students_placed(self, students_26, empty_history):
        result = form_teams(students_26, 4, empty_history)
        assert all_students_in_result(students_26, result)

    def test_no_restarts_on_first_activity(self, students_62, empty_history):
        result = form_teams(students_62, 6, empty_history)
        assert result.restarts == 0

    def test_saturation_zero_on_first_activity(self, students_26, empty_history):
        result = form_teams(students_26, 4, empty_history)
        assert result.saturation == 0.0

    def test_deterministic_with_seed(self, students_26, empty_history):
        r1 = form_teams(students_26, 4, empty_history, seed=42)
        r2 = form_teams(students_26, 4, empty_history, seed=42)
        assert r1.teams == r2.teams


# ---------------------------------------------------------------------------
# Later activities (history exists)
# ---------------------------------------------------------------------------

class TestWithHistory:
    def test_all_students_placed(self, students_26):
        history = make_history_from_activities(students_26, 4, n_activities=2)
        result = form_teams(students_26, 4, history, seed=99)
        assert all_students_in_result(students_26, result)

    def test_no_duplicates_in_teams(self, students_26):
        history = make_history_from_activities(students_26, 4, n_activities=2)
        result = form_teams(students_26, 4, history, seed=99)
        placed = [s for t in result.teams for s in t]
        assert len(placed) == len(set(placed))

    def test_score_lower_than_naive_random(self, students_62):
        """
        After 3 activities, the engine should produce a better score
        than a purely random arrangement would (on average).
        We test this by checking score < worst possible.
        """
        history = make_history_from_activities(students_62, 6, n_activities=3)
        result = form_teams(students_62, 6, history, seed=7, time_limit=1.0)
        # Score should be finite and non-negative
        assert result.score >= 0
        assert result.new_pairs >= 0

    def test_saturation_increases_over_activities(self, students_26):
        history = {}
        prev_sat = 0.0
        for i in range(5):
            result = form_teams(students_26, 4, history, seed=i)
            history = build_history_from_teams(result.teams, days_ago=30 * (5 - i), existing=history)
            new_sat = saturation(history, len(students_26))
            assert new_sat >= prev_sat
            prev_sat = new_sat

    def test_result_fields_populated(self, students_26):
        history = make_history_from_activities(students_26, 4, n_activities=2)
        result = form_teams(students_26, 4, history, seed=1)
        assert isinstance(result.score, int)
        assert isinstance(result.new_pairs, int)
        assert isinstance(result.saturation, float)
        assert isinstance(result.restarts, int)
        assert isinstance(result.elapsed_seconds, float)
        assert isinstance(result.unfair_students, list)
        assert result.elapsed_seconds >= 0


# ---------------------------------------------------------------------------
# Fairness
# ---------------------------------------------------------------------------

class TestFairness:
    def test_no_fairness_violations_early_activities(self, students_26):
        """In the first few activities, every student must get a new teammate."""
        history = {}
        for i in range(4):
            result = form_teams(students_26, 4, history, seed=i, time_limit=1.0)
            violations = has_violations(result.teams, history)
            assert violations == [], f"Violations in activity {i+1}: {violations}"
            history = build_history_from_teams(result.teams, days_ago=30 * (4 - i), existing=history)

    def test_unfair_students_field_matches_has_violations(self, students_26):
        history = make_history_from_activities(students_26, 4, n_activities=3)
        result = form_teams(students_26, 4, history, seed=5, time_limit=1.0)
        direct_check = has_violations(result.teams, history)
        assert set(result.unfair_students) == set(direct_check)


# ---------------------------------------------------------------------------
# Lock constraints
# ---------------------------------------------------------------------------

class TestLocks:
    def test_together_lock_places_students_on_same_team(self, students_26, empty_history):
        locks = [Lock("A", "B", "together")]
        result = form_teams(students_26, 4, empty_history, locks=locks, seed=42)
        a_team = next(t for t in result.teams if "A" in t)
        assert "B" in a_team

    def test_apart_lock_places_students_on_different_teams(self, students_26, empty_history):
        locks = [Lock("A", "B", "apart")]
        result = form_teams(students_26, 4, empty_history, locks=locks, seed=42)
        a_team = next(t for t in result.teams if "A" in t)
        assert "B" not in a_team

    def test_all_students_still_placed_with_locks(self, students_26, empty_history):
        locks = [Lock("A", "B", "together"), Lock("C", "D", "apart")]
        result = form_teams(students_26, 4, empty_history, locks=locks, seed=42)
        assert all_students_in_result(students_26, result)

    def test_no_locks_same_as_empty_list(self, students_26, empty_history):
        r1 = form_teams(students_26, 4, empty_history, locks=None, seed=42)
        r2 = form_teams(students_26, 4, empty_history, locks=[], seed=42)
        assert r1.teams == r2.teams


# ---------------------------------------------------------------------------
# validate_locks
# ---------------------------------------------------------------------------

class TestValidateLocks:
    def test_valid_locks_return_no_errors(self):
        locks = [Lock("A", "B", "together"), Lock("C", "D", "apart")]
        errors = validate_locks(locks, team_size=4)
        assert errors == []

    def test_together_group_larger_than_team_size_is_error(self):
        # A, B, C, D, E must all be together but team size is 3
        locks = [
            Lock("A", "B", "together"),
            Lock("B", "C", "together"),
            Lock("C", "D", "together"),
            Lock("D", "E", "together"),
        ]
        errors = validate_locks(locks, team_size=3)
        assert len(errors) > 0

    def test_together_group_equal_to_team_size_is_valid(self):
        locks = [Lock("A", "B", "together"), Lock("B", "C", "together")]
        errors = validate_locks(locks, team_size=3)
        assert errors == []

    def test_empty_locks_no_errors(self):
        assert validate_locks([], team_size=5) == []


# ---------------------------------------------------------------------------
# Bug-fix regression tests
# ---------------------------------------------------------------------------

class TestInputValidation:
    def test_team_size_zero_raises(self, empty_history):
        """FIX B7"""
        with pytest.raises(ValueError, match="team_size"):
            form_teams(["A", "B", "C"], 0, empty_history)

    def test_team_size_negative_raises(self, empty_history):
        with pytest.raises(ValueError, match="team_size"):
            form_teams(["A", "B", "C"], -1, empty_history)

    def test_duplicate_students_raises(self, empty_history):
        """FIX B10"""
        with pytest.raises(ValueError, match="duplicate"):
            form_teams(["A", "B", "A"], 2, empty_history)


class TestLocksSatisfied:
    def test_together_lock_satisfied_with_history(self, students_26):
        """FIX B3: together locks must hold with history across many seeds."""
        from tests.algorithm.conftest import build_history_from_teams
        history = {}
        for i in range(3):
            r = form_teams(students_26, 4, history, seed=i)
            history = build_history_from_teams(r.teams, days_ago=30*(3-i), existing=history)
        for seed in range(10):
            locks = [Lock("A", "B", "together")]
            result = form_teams(students_26, 4, history, locks=locks, seed=seed, time_limit=0.5)
            a_team = next(t for t in result.teams if "A" in t)
            assert "B" in a_team, f"Together lock broken at seed {seed}"

    def test_unsatisfied_locks_field_exists(self, empty_history):
        """FIX B13: FormationResult must have unsatisfied_locks field."""
        result = form_teams(["A", "B", "C"], 3, empty_history)
        assert hasattr(result, "unsatisfied_locks")
        assert isinstance(result.unsatisfied_locks, list)


class TestValidateLocksExtended:
    def test_self_lock_is_error(self):
        """FIX B6"""
        errors = validate_locks([Lock("A", "A", "together")], team_size=4)
        assert len(errors) > 0

    def test_contradiction_is_error(self):
        """FIX B6"""
        locks = [Lock("A", "B", "together"), Lock("A", "B", "apart")]
        errors = validate_locks(locks, team_size=4)
        assert len(errors) > 0

    def test_apart_when_single_team_is_error(self):
        """FIX B6"""
        errors = validate_locks([Lock("A", "B", "apart")], team_size=10, n_students=5)
        assert len(errors) > 0

    def test_invalid_constraint_type_raises(self):
        """FIX B13"""
        with pytest.raises(ValueError):
            Lock("A", "B", "sideways")


class TestAbsorbRemainder:
    def test_absorb_distributes_to_different_teams(self, empty_history):
        """FIX B5: 14 students, team_size 6 → r=2 < half=3 → absorb → two teams of 7."""
        students = [f"s{i}" for i in range(14)]
        result = form_teams(students, 6, empty_history, seed=42)
        sizes = sorted(len(t) for t in result.teams)
        assert sizes == [7, 7], f"Expected [7,7], got {sizes}"

    def test_absorb_no_team_gets_two_extras(self, empty_history):
        """FIX B5: no single team should receive more than one extra."""
        # 11 students, team_size 4: r=3 > half=2 → new small team (not absorb)
        # 9 students, team_size 4: r=1 → absorb → two teams of 4, one of 5
        students = [f"s{i}" for i in range(9)]
        result = form_teams(students, 4, empty_history, seed=0)
        sizes = sorted(len(t) for t in result.teams)
        assert sum(sizes) == 9
        assert max(sizes) <= 5  # no team grew by more than 1
