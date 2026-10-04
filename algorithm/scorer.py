"""
scorer.py — Pair scoring and arrangement evaluation.

Pair history is a sparse dict:
    key   : (student_a, student_b)  — always sorted so (A,B) == (B,A)
    value : (overlap_count, days_since_last_together)

A missing key means the two students have never worked together → score = 0.

Scoring formula:
    score(A, B) = overlap_count * 1000 - days_since_last_together

    Never met          →    0   (best possible)
    Met once, 30d ago  →  970
    Met once, 0d ago   → 1000
    Met twice, 5d ago  → 1995   (worse)

Higher score = worse pairing. Goal: minimise total arrangement score.

Two-key ranking used throughout:
    primary   : total score     ascending  (lower is better)
    secondary : new_pairs count descending (more new pairs is better)
"""

from __future__ import annotations
from itertools import combinations

# Type alias used across the algorithm package.
# Maps (student_a, student_b) → (overlap_count, days_since_last_together)
PairHistory = dict[tuple[str, str], tuple[int, int]]


def pair_key(a: str, b: str) -> tuple[str, str]:
    """Canonical sorted key so (A,B) and (B,A) always resolve to the same entry."""
    return (a, b) if a < b else (b, a)


def pair_score(a: str, b: str, history: PairHistory) -> int:
    """
    Score for placing a and b on the same team.
    Returns 0 if they have never worked together.
    """
    entry = history.get(pair_key(a, b))
    if entry is None:
        return 0
    count, days_ago = entry
    return count * 1000 - days_ago


def team_score(team: list[str], history: PairHistory) -> int:
    """Sum of pair scores for every pair within one team."""
    return sum(pair_score(a, b, history) for a, b in combinations(team, 2))


def marginal_score(student: str, team: list[str], history: PairHistory) -> int:
    """
    Extra cost of adding student to an existing team.
    This is what the greedy step minimises at each placement.
    """
    return sum(pair_score(student, m, history) for m in team)


def arrangement_score(teams: list[list[str]], history: PairHistory) -> int:
    """Total score across all teams. Lower is better."""
    return sum(team_score(t, history) for t in teams)


def count_new_pairs(teams: list[list[str]], history: PairHistory) -> int:
    """
    Number of (A, B) pairs across all teams where the two have never
    worked together. Used as a tie-breaker: more new pairs = better.
    """
    return sum(
        1
        for team in teams
        for a, b in combinations(team, 2)
        if history.get(pair_key(a, b)) is None
    )


def saturation(history: PairHistory, n_students: int) -> float:
    """
    Fraction of all possible pairs that have worked together at least once.
    0.0 = no history yet.  1.0 = fully exhausted (everyone has met everyone).
    """
    if n_students < 2:
        return 0.0
    total_possible = n_students * (n_students - 1) // 2
    return len(history) / total_possible


def is_better(
    cand_score: int,
    cand_new: int,
    best_score: int,
    best_new: int,
) -> bool:
    """
    Return True if (cand_score, cand_new) is strictly better than
    (best_score, best_new) under the two-key ranking.
    """
    if cand_score < best_score:
        return True
    if cand_score == best_score and cand_new > best_new:
        return True
    return False
