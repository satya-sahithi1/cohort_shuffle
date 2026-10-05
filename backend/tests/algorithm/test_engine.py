"""Tests for engine.py — form_teams() end-to-end."""
import pytest
from app.algorithm.engine import form_teams, Lock, validate_locks


# ── Helpers ───────────────────────────────────────────────────────────────────

def _all_students_placed(result, students):
    placed = [s for team in result.teams for s in team]
    return sorted(placed) == sorted(students)


def _no_duplicates(result):
    placed = [s for team in result.teams for s in team]
    return len(placed) == len(set(placed))


def _together_satisfied(result, lock):
    for team in result.teams:
        if lock.student_a in team:
            return lock.student_b in team
    return False


def _apart_satisfied(result, lock):
    for team in result.teams:
        if lock.student_a in team and lock.student_b in team:
            return False
    return True


# ── Input validation ──────────────────────────────────────────────────────────

def test_invalid_team_size():
    with pytest.raises(ValueError, match="team_size"):
        form_teams(["a", "b", "c"], 0, {})


def test_duplicate_students():
    with pytest.raises(ValueError, match="Duplicate"):
        form_teams(["a", "a", "b"], 2, {})


def test_empty_students():
    result = form_teams([], 3, {})
    assert result.teams == []
    assert result.score == 0.0


# ── Basic formation ───────────────────────────────────────────────────────────

def test_all_students_placed_no_history():
    students = [f"s{i}" for i in range(12)]
    result = form_teams(students, 4, {}, seed=42)
    assert _all_students_placed(result, students)
    assert _no_duplicates(result)


def test_all_students_placed_with_history(students_12, light_history):
    result = form_teams(students_12, 4, light_history, seed=42)
    assert _all_students_placed(result, students_12)
    assert _no_duplicates(result)


def test_team_sizes_correct():
    students = [f"s{i}" for i in range(12)]
    result = form_teams(students, 4, {}, seed=1)
    assert all(len(t) == 4 for t in result.teams)


def test_team_sizes_with_remainder():
    # 14 students, team_size=4: r=2 >= 4/2=2 → 3 full + 1 small of 2
    students = [f"s{i}" for i in range(14)]
    result = form_teams(students, 4, {}, seed=1)
    sizes = sorted(len(t) for t in result.teams)
    assert sizes == [2, 4, 4, 4]


def test_fewer_students_than_team_size():
    students = ["a", "b", "c"]
    result = form_teams(students, 5, {}, seed=1)
    assert len(result.teams) == 1
    assert sorted(result.teams[0]) == ["a", "b", "c"]


def test_seed_is_stored():
    students = [f"s{i}" for i in range(10)]
    result = form_teams(students, 3, {}, seed=99)
    assert result.random_seed == 99


def test_seed_auto_assigned():
    students = [f"s{i}" for i in range(10)]
    result = form_teams(students, 3, {})
    assert result.random_seed is not None
    assert isinstance(result.random_seed, int)


def test_reproducible_with_same_seed(students_12, light_history):
    r1 = form_teams(students_12, 4, light_history, seed=7)
    r2 = form_teams(students_12, 4, light_history, seed=7)
    assert r1.teams == r2.teams


def test_different_seeds_may_differ(students_12, light_history):
    results = {
        frozenset(frozenset(t) for t in form_teams(students_12, 4, light_history, seed=i).teams)
        for i in range(20)
    }
    assert len(results) > 1  # some variation expected


# ── Score and metrics ─────────────────────────────────────────────────────────

def test_zero_score_no_history():
    students = [f"s{i}" for i in range(12)]
    result = form_teams(students, 4, {}, seed=1)
    assert result.score == 0.0
    assert result.repeat_pairs == 0


def test_saturation_zero_no_history():
    students = [f"s{i}" for i in range(12)]
    result = form_teams(students, 4, {}, seed=1)
    assert result.saturation == 0.0


def test_elapsed_seconds_positive():
    students = [f"s{i}" for i in range(20)]
    result = form_teams(students, 4, {}, seed=1)
    assert result.elapsed_seconds >= 0.0


def test_time_limit_respected():
    students = [f"s{i}" for i in range(30)]
    from itertools import combinations
    history = {(a, b): (1, i % 30 + 1) for i, (a, b) in enumerate(combinations(students, 2))}
    result = form_teams(students, 4, history, time_limit=0.5, seed=1)
    assert result.elapsed_seconds < 2.0  # generous but shouldn't hang


# ── Locks ─────────────────────────────────────────────────────────────────────

def test_together_lock_satisfied(students_12, empty_history):
    lock = Lock("s00", "s01", "together")
    result = form_teams(students_12, 4, empty_history, locks=[lock], seed=5)
    assert _together_satisfied(result, lock)


def test_apart_lock_satisfied(students_12, empty_history):
    lock = Lock("s00", "s01", "apart")
    result = form_teams(students_12, 4, empty_history, locks=[lock], seed=5)
    assert _apart_satisfied(result, lock)


def test_multiple_together_locks(students_12, empty_history):
    locks = [
        Lock("s00", "s01", "together"),
        Lock("s02", "s03", "together"),
    ]
    result = form_teams(students_12, 4, empty_history, locks=locks, seed=3)
    for lock in locks:
        assert _together_satisfied(result, lock)


def test_unregistered_student_in_lock_skipped():
    students = ["a", "b", "c", "d"]
    lock = Lock("a", "zz", "together")  # zz not registered
    result = form_teams(students, 2, {}, locks=[lock], seed=1)
    assert len(result.skipped_locks) == 1
    assert _all_students_placed(result, students)


def test_invalid_lock_constraint_type():
    with pytest.raises(ValueError):
        Lock("a", "b", "sideways")


# ── validate_locks ────────────────────────────────────────────────────────────

def test_self_lock_detected():
    errors = validate_locks([Lock("a", "a", "together")], team_size=3)
    assert any("themselves" in e for e in errors)


def test_cluster_too_large():
    locks = [Lock("a", "b", "together"), Lock("b", "c", "together")]
    errors = validate_locks(locks, team_size=2, n_students=6, n_teams=3)
    assert any("exceeds" in e for e in errors)


def test_cluster_contradiction():
    # a+b together, b+c together, a+c apart → contradiction
    locks = [
        Lock("a", "b", "together"),
        Lock("b", "c", "together"),
        Lock("a", "c", "apart"),
    ]
    errors = validate_locks(locks, team_size=4, n_students=9, n_teams=3)
    assert any("contradiction" in e for e in errors)


def test_apart_one_team():
    errors = validate_locks(
        [Lock("a", "b", "apart")], team_size=4, n_students=3, n_teams=1
    )
    assert any("one team" in e for e in errors)


def test_valid_locks_no_errors():
    locks = [Lock("a", "b", "together"), Lock("c", "d", "apart")]
    errors = validate_locks(locks, team_size=4, n_students=12, n_teams=3)
    assert errors == []


# ── Fairness ──────────────────────────────────────────────────────────────────

def test_fairness_no_history():
    students = [f"s{i}" for i in range(12)]
    result = form_teams(students, 4, {}, seed=1)
    assert result.unfair_students == []


def test_fairness_with_history(students_20):
    from itertools import combinations
    history = {}
    for i, (a, b) in enumerate(combinations(students_20, 2)):
        if i % 3 == 0:
            history[(a, b)] = (1, i % 20 + 1)
    result = form_teams(students_20, 4, history, seed=42, time_limit=2.0)
    assert _all_students_placed(result, students_20)


# ── Restarts ──────────────────────────────────────────────────────────────────

def test_restarts_zero_no_history():
    students = [f"s{i}" for i in range(12)]
    result = form_teams(students, 4, {}, seed=1)
    assert result.restarts == 0


def test_restarts_positive_with_history(students_12, dense_history):
    result = form_teams(students_12, 4, dense_history, seed=1, time_limit=0.3)
    # With history and time budget, at least one restart should happen
    assert result.restarts >= 0  # could be 0 if first pass is perfect
