"""Tests for scorer.py"""
import pytest
from app.algorithm.scorer import (
    pair_key, has_met, pair_cost, team_cost, marginal_cost,
    arrangement_cost, count_repeat_pairs, saturation,
    fairness_cost, is_better, FAIRNESS_PENALTY,
)


# ── pair_key ──────────────────────────────────────────────────────────────────

def test_pair_key_canonical():
    assert pair_key("b", "a") == ("a", "b")
    assert pair_key("a", "b") == ("a", "b")


def test_pair_key_same_regardless_of_order():
    assert pair_key("s10", "s02") == pair_key("s02", "s10")


# ── has_met ───────────────────────────────────────────────────────────────────

def test_has_met_true():
    h = {("a", "b"): (1, 5)}
    assert has_met("a", "b", h) is True
    assert has_met("b", "a", h) is True  # canonical lookup


def test_has_met_false():
    assert has_met("a", "b", {}) is False


# ── pair_cost ─────────────────────────────────────────────────────────────────

def test_pair_cost_never_met():
    assert pair_cost("a", "b", {}) == 0.0


def test_pair_cost_met_once_recently():
    # count=1, days=0 → 1 + 1/(1+0/30) = 1 + 1.0 = 2.0
    h = {("a", "b"): (1, 0)}
    assert pair_cost("a", "b", h) == pytest.approx(2.0)


def test_pair_cost_met_once_long_ago():
    # count=1, days=30 → 1 + 1/(1+1) = 1.5
    h = {("a", "b"): (1, 30)}
    assert pair_cost("a", "b", h) == pytest.approx(1.5)


def test_pair_cost_count_dominates():
    # count=2 old pair vs count=1 recent pair
    # count=2, days=1000 → 2 + 1/(1+1000/30) ≈ 2.03
    # count=1, days=0    → 1 + 1.0 = 2.0
    h_old = {("a", "b"): (2, 1000)}
    h_new = {("a", "b"): (1, 0)}
    assert pair_cost("a", "b", h_old) > pair_cost("a", "b", h_new)


def test_pair_cost_never_negative():
    for days in [0, 1, 30, 365, 10000]:
        for count in [1, 2, 5]:
            h = {("a", "b"): (count, days)}
            assert pair_cost("a", "b", h) >= 0


def test_pair_cost_recency_breaks_tie():
    # Same count, more recent = higher cost (worse)
    h_recent = {("a", "b"): (1, 1)}
    h_stale = {("a", "b"): (1, 100)}
    assert pair_cost("a", "b", h_recent) > pair_cost("a", "b", h_stale)


# ── team_cost ─────────────────────────────────────────────────────────────────

def test_team_cost_no_history():
    assert team_cost(["a", "b", "c"], {}) == 0.0


def test_team_cost_one_pair():
    h = {("a", "b"): (1, 30)}
    assert team_cost(["a", "b", "c"], h) == pytest.approx(1.5)


# ── marginal_cost ─────────────────────────────────────────────────────────────

def test_marginal_cost_empty_team():
    assert marginal_cost("a", [], {}) == 0.0


def test_marginal_cost_no_history():
    assert marginal_cost("a", ["b", "c"], {}) == 0.0


# ── count_repeat_pairs ────────────────────────────────────────────────────────

def test_count_repeat_pairs_none():
    teams = [["a", "b"], ["c", "d"]]
    assert count_repeat_pairs(teams, {}) == 0


def test_count_repeat_pairs_some():
    h = {("a", "b"): (1, 1), ("c", "d"): (1, 1)}
    teams = [["a", "b"], ["c", "d"]]
    assert count_repeat_pairs(teams, h) == 2


def test_count_repeat_pairs_cross_team_not_counted():
    # a and c have met but are on different teams — not a repeat
    h = {("a", "c"): (1, 1)}
    teams = [["a", "b"], ["c", "d"]]
    assert count_repeat_pairs(teams, h) == 0


# ── saturation ────────────────────────────────────────────────────────────────

def test_saturation_empty():
    assert saturation({}, ["a", "b", "c"]) == 0.0


def test_saturation_full():
    # 3 students, 3 possible pairs, all met
    h = {("a", "b"): (1, 1), ("a", "c"): (1, 1), ("b", "c"): (1, 1)}
    assert saturation(h, ["a", "b", "c"]) == pytest.approx(1.0)


def test_saturation_clamped_to_1():
    # More history keys than possible pairs (shouldn't happen but be safe)
    h = {("a", "b"): (1, 1), ("a", "c"): (1, 1), ("b", "c"): (2, 1)}
    assert saturation(h, ["a", "b", "c"]) <= 1.0


def test_saturation_only_counts_registered():
    # x and y have met but are not in the registered list
    h = {("a", "b"): (1, 1), ("x", "y"): (1, 1)}
    assert saturation(h, ["a", "b", "c"]) == pytest.approx(1 / 3)


def test_saturation_single_student():
    assert saturation({}, ["a"]) == 0.0


# ── fairness_cost ─────────────────────────────────────────────────────────────

def test_fairness_cost_no_history():
    teams = [["a", "b"], ["c", "d"]]
    assert fairness_cost(teams, {}, ["a", "b", "c", "d"]) == 0.0


def test_fairness_cost_all_repeat_team():
    # a and b have met — a has no new teammates available (c,d also met a)
    h = {("a", "b"): (1, 1), ("a", "c"): (1, 1), ("a", "d"): (1, 1)}
    teams = [["a", "b"], ["c", "d"]]
    cost = fairness_cost(teams, h, ["a", "b", "c", "d"])
    assert cost == FAIRNESS_PENALTY  # only a is a violator


def test_fairness_cost_no_new_person_available():
    # a has met b and c (everyone) — no new person exists — not a violation
    # b has met a but NOT c — b has a new person available but b's team has a new teammate
    # so no violation either
    h = {("a", "b"): (1, 1), ("a", "c"): (1, 1), ("b", "c"): (1, 1)}
    teams = [["a", "b"], ["c"]]
    cost = fairness_cost(teams, h, ["a", "b", "c"])
    assert cost == 0.0  # a has met all classmates, nothing to fix


# ── is_better ─────────────────────────────────────────────────────────────────

def test_is_better_lower_cost():
    assert is_better(1.0, 1, 2.0, 1) is True


def test_is_better_higher_cost():
    assert is_better(2.0, 1, 1.0, 1) is False


def test_is_better_same_cost_fewer_repeats():
    assert is_better(1.0, 0, 1.0, 1) is True


def test_is_better_same_cost_more_repeats():
    assert is_better(1.0, 2, 1.0, 1) is False


def test_is_better_identical():
    assert is_better(1.0, 1, 1.0, 1) is False
