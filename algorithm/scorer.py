"""
scorer.py — Pair scoring and arrangement evaluation.

FIX B1: Old formula count*1000 - days_ago goes negative for days_ago > 1000,
         making old repeats score better than new pairs. New formula clamps
         recency into [0, RECENCY_SCALE-1] so score is always >= 1 for met pairs.

FIX B2: Added has_met() — single authoritative check for "have these two met?"
         based on key presence only. Never derived from pair_score > 0.

FIX B8: saturation() accepts optional `registered` list and clamps to [0.0, 1.0].
"""

from __future__ import annotations
from itertools import combinations

PairHistory = dict[tuple[str, str], tuple[int, int]]

RECENCY_SCALE = 1000


def pair_key(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a < b else (b, a)


def has_met(a: str, b: str, history: PairHistory) -> bool:
    """FIX B2: key-presence check only — never use pair_score > 0 for this."""
    return pair_key(a, b) in history


def pair_score(a: str, b: str, history: PairHistory) -> int:
    """
    FIX B1: always >= 1 for any met pair, 0 for never-met.
    score = count * RECENCY_SCALE + (RECENCY_SCALE - 1 - min(days, RECENCY_SCALE-1))
    """
    entry = history.get(pair_key(a, b))
    if entry is None:
        return 0
    count, days_ago = entry
    recency_penalty = RECENCY_SCALE - 1 - min(days_ago, RECENCY_SCALE - 1)
    return count * RECENCY_SCALE + recency_penalty


def team_score(team: list[str], history: PairHistory) -> int:
    return sum(pair_score(a, b, history) for a, b in combinations(team, 2))


def marginal_score(student: str, team: list[str], history: PairHistory) -> int:
    return sum(pair_score(student, m, history) for m in team)


def arrangement_score(teams: list[list[str]], history: PairHistory) -> int:
    return sum(team_score(t, history) for t in teams)


def count_new_pairs(teams: list[list[str]], history: PairHistory) -> int:
    """FIX B2: uses has_met for consistency."""
    return sum(
        1
        for team in teams
        for a, b in combinations(team, 2)
        if not has_met(a, b, history)
    )


def saturation(
    history: PairHistory,
    n_students: int,
    registered: list[str] | None = None,
) -> float:
    """FIX B8: filter to registered set, clamp to [0.0, 1.0]."""
    if n_students < 2:
        return 0.0
    if registered is not None:
        reg_set = set(registered)
        n = len(reg_set)
        if n < 2:
            return 0.0
        total_possible = n * (n - 1) // 2
        count = sum(1 for key in history if key[0] in reg_set and key[1] in reg_set)
    else:
        total_possible = n_students * (n_students - 1) // 2
        count = len(history)
    return min(count / total_possible, 1.0)


def is_better(cand_score: int, cand_new: int, best_score: int, best_new: int) -> bool:
    if cand_score < best_score:
        return True
    if cand_score == best_score and cand_new > best_new:
        return True
    return False
