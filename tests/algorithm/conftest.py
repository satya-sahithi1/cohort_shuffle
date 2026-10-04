"""
conftest.py — Shared pytest fixtures for algorithm tests.

Fixtures available to all test files in this folder:
  - students_26       : alphabet A-Z
  - students_62       : s01..s62
  - students_120      : s001..s120
  - empty_history     : {}
  - small_history     : a few hand-crafted pairs
  - saturated_history : every pair in a 10-student group has met
"""

import pytest
from backend.algorithm.scorer import PairHistory, pair_key


# ---------------------------------------------------------------------------
# Student lists
# ---------------------------------------------------------------------------

@pytest.fixture
def students_26() -> list[str]:
    return list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")


@pytest.fixture
def students_62() -> list[str]:
    return [f"s{i:02d}" for i in range(1, 63)]


@pytest.fixture
def students_120() -> list[str]:
    return [f"s{i:03d}" for i in range(1, 121)]


@pytest.fixture
def students_10() -> list[str]:
    return [f"s{i:02d}" for i in range(1, 11)]


# ---------------------------------------------------------------------------
# Pair histories
# ---------------------------------------------------------------------------

@pytest.fixture
def empty_history() -> PairHistory:
    return {}


@pytest.fixture
def small_history() -> PairHistory:
    """
    A-B worked together once, 30 days ago.
    A-C worked together twice, 5 days ago.
    D-E worked together once, 100 days ago.
    """
    h: PairHistory = {}
    h[pair_key("A", "B")] = (1, 30)
    h[pair_key("A", "C")] = (2, 5)
    h[pair_key("D", "E")] = (1, 100)
    return h


@pytest.fixture
def saturated_history(students_10) -> PairHistory:
    """Every pair in students_10 has worked together once, 50 days ago."""
    h: PairHistory = {}
    students = students_10
    for i, a in enumerate(students):
        for b in students[i + 1:]:
            h[pair_key(a, b)] = (1, 50)
    return h


def build_history_from_teams(
    teams: list[list[str]],
    days_ago: int,
    existing: PairHistory | None = None,
) -> PairHistory:
    """
    Helper (not a fixture) to build or extend a PairHistory from a
    list of teams. Useful in tests that need multi-activity histories.
    """
    h: PairHistory = dict(existing) if existing else {}
    for team in teams:
        for i, a in enumerate(team):
            for b in team[i + 1:]:
                key = pair_key(a, b)
                count, _ = h.get(key, (0, days_ago))
                h[key] = (count + 1, days_ago)
    return h
