"""
Scoring functions for the cohort shuffle algorithm.

Pair history is sparse: only pairs who have actually worked together
are stored. A missing key means score = 0 (never met).

score(A, B) = overlap_count * 1000 - days_since_last_together
  - Never met        → 0    (best)
  - Met once 30d ago → 970
  - Met twice 5d ago → 1995 (worse)

Higher score = worse pairing. Goal: minimise total score.
"""

from __future__ import annotations
from itertools import combinations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .engine import PairHistory


def pair_score(a: str, b: str, pair_history: "PairHistory") -> int:
    """
    Score for placing student a and b on the same team.
    Returns 0 if they have never worked together.
    """
    key = _key(a, b)
    entry = pair_history.get(key)
    if entry is None:
        return 0
    count, days_ago = entry
    return count * 1000 - days_ago


def team_score(team: list[str], pair_history: "PairHistory") -> int:
    """Sum of pair scores for all pairs within a team."""
    return sum(pair_score(a, b, pair_history) for a, b in combinations(team, 2))


def marginal_score(student: str, team: list[str], pair_history: "PairHistory") -> int:
    """Extra cost of adding student to an existing (possibly empty) team."""
    return sum(pair_score(student, m, pair_history) for m in team)


def arrangement_score(teams: list[list[str]], pair_history: "PairHistory") -> int:
    """Total score across all teams in an arrangement."""
    return sum(team_score(t, pair_history) for t in teams)


def count_new_pairs(teams: list[list[str]], pair_history: "PairHistory") -> int:
    """
    Number of (A, B) pairs in this arrangement where they have never
    worked together before. Higher = better (used as tie-breaker).
    """
    total = 0
    for team in teams:
        for a, b in combinations(team, 2):
            if pair_history.get(_key(a, b)) is None:
                total += 1
    return total


def saturation(pair_history: "PairHistory", n_students: int) -> float:
    """
    Fraction of all possible pairs that have worked together at least once.
    0.0 = no history, 1.0 = fully exhausted.
    """
    if n_students < 2:
        return 0.0
    total_possible = n_students * (n_students - 1) // 2
    return len(pair_history) / total_possible


def is_better(
    cand_score: int,
    cand_new: int,
    best_score: int,
    best_new: int,
) -> bool:
    """
    Two-key comparison: lower score wins; ties broken by more new pairs.
    """
    if cand_score < best_score:
        return True
    if cand_score == best_score and cand_new > best_new:
        return True
    return False


def _key(a: str, b: str) -> tuple[str, str]:
    """Canonical (sorted) key so (A,B) and (B,A) map to the same entry."""
    return (a, b) if a < b else (b, a)
