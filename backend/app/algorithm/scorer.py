"""
scorer.py — Pair scoring and arrangement evaluation.

Scoring formula (from spec):
  Never-met pair  → cost = 0
  Met pair        → cost = count + 1 / (1 + days_since_last / 30)

  The integer part (count) always dominates so a pair met twice is
  always worse than a pair met once, regardless of recency.
  The fractional part (0 < f < 1) breaks ties: a more recent repeat
  scores higher (worse) than a stale one.
  This formula never goes negative and never divides by zero.

Fairness penalty:
  A student is "unfair" if every teammate has already worked with them
  AND at least one classmate they have NEVER worked with exists.
  We add a large flat penalty per unfair student so the optimiser
  strongly prefers fixing fairness over marginal score improvements.
"""

from __future__ import annotations
from itertools import combinations

# PairHistory: maps canonical pair → (count, days_since_last)
# "Canonical" means the lexicographically smaller id comes first.
PairHistory = dict[tuple[str, str], tuple[int, int]]

# Fairness penalty per violating student — large enough to dominate pair scores
FAIRNESS_PENALTY = 10_000


def pair_key(a: str, b: str) -> tuple[str, str]:
    """Return canonical (smaller, larger) key for a pair."""
    return (a, b) if a < b else (b, a)


def has_met(a: str, b: str, history: PairHistory) -> bool:
    """True if this pair appears anywhere in history."""
    return pair_key(a, b) in history


def pair_cost(a: str, b: str, history: PairHistory) -> float:
    """
    Cost for placing a and b on the same team.

    Returns 0.0 for never-met pairs.
    For met pairs: count + 1/(1 + days/30)
      - count is the integer part → always dominates
      - recency fraction is in (0, 1) → breaks ties only
    """
    entry = history.get(pair_key(a, b))
    if entry is None:
        return 0.0
    count, days = entry
    recency = 1.0 / (1.0 + days / 30.0)
    return count + recency


def team_cost(team: list[str], history: PairHistory) -> float:
    """Sum of pair costs for all pairs in a team."""
    return sum(pair_cost(a, b, history) for a, b in combinations(team, 2))


def marginal_cost(student: str, team: list[str], history: PairHistory) -> float:
    """Cost of adding student to team (sum of costs with each existing member)."""
    return sum(pair_cost(student, m, history) for m in team)


def arrangement_cost(teams: list[list[str]], history: PairHistory) -> float:
    """Total cost across all teams."""
    return sum(team_cost(t, history) for t in teams)


def count_repeat_pairs(teams: list[list[str]], history: PairHistory) -> int:
    """Count pairs within teams that have met before."""
    return sum(
        1
        for team in teams
        for a, b in combinations(team, 2)
        if has_met(a, b, history)
    )


def fairness_cost(
    teams: list[list[str]],
    history: PairHistory,
    all_students: list[str],
) -> float:
    """
    Penalty for fairness violations.

    A student is a violator if:
      - All their teammates have worked with them before, AND
      - At least one student in all_students has NEVER worked with them.

    Returns FAIRNESS_PENALTY * number_of_violators.
    """
    all_set = set(all_students)
    penalty = 0.0
    for team in teams:
        for student in team:
            teammates = [m for m in team if m != student]
            if not teammates:
                continue
            all_old_teammates = all(has_met(student, t, history) for t in teammates)
            if not all_old_teammates:
                continue
            # Student has all-repeat team — check if any new person exists
            has_new_person_available = any(
                not has_met(student, s, history)
                for s in all_set
                if s != student
            )
            if has_new_person_available:
                penalty += FAIRNESS_PENALTY
    return penalty


def total_cost(
    teams: list[list[str]],
    history: PairHistory,
    all_students: list[str],
) -> float:
    """Arrangement cost + fairness penalty. Lower is better."""
    return arrangement_cost(teams, history) + fairness_cost(teams, history, all_students)


def saturation(history: PairHistory, registered: list[str]) -> float:
    """
    Fraction of possible unique pairs among registered students
    that have already worked together. Clamped to [0.0, 1.0].
    """
    n = len(registered)
    if n < 2:
        return 0.0
    reg_set = set(registered)
    total_possible = n * (n - 1) // 2
    seen = sum(1 for key in history if key[0] in reg_set and key[1] in reg_set)
    return min(seen / total_possible, 1.0)


def is_better(
    cand_cost: float,
    cand_repeats: int,
    best_cost: float,
    best_repeats: int,
) -> bool:
    """
    True if candidate result is strictly better than current best.
    Lower cost wins; tie broken by fewer repeats.
    """
    if cand_cost < best_cost:
        return True
    if cand_cost == best_cost and cand_repeats < best_repeats:
        return True
    return False
