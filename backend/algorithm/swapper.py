"""
swapper.py — Local swap optimisation.

After greedy placement, this step tries every possible swap between
two teams and keeps it if it improves the (score, new_pairs) ranking.

Key efficiency rule: only attempt swaps where at least one of the two
students is a "conflict student" — someone who already has at least one
repeat on their current team. In early activities this set is empty and
the entire step is skipped in O(n) time.

The loop runs until a full pass produces no improvement (local optimum).
"""

from __future__ import annotations
from itertools import combinations

from .scorer import PairHistory, team_score, pair_score, pair_key, is_better


def optimise(
    teams: list[list[str]],
    history: PairHistory,
) -> list[list[str]]:
    """
    Run swap passes until no improvement is found.
    Modifies `teams` in-place and returns it.
    """
    if len(teams) < 2:
        return teams

    # Fast exit: if no conflict students exist, nothing to improve
    conflict = _conflict_students(teams, history)
    if not conflict:
        return teams

    improved = True
    while improved:
        improved = False
        conflict = _conflict_students(teams, history)
        if not conflict:
            break

        for i, j in combinations(range(len(teams)), 2):
            for si in range(len(teams[i])):
                for sj in range(len(teams[j])):
                    s1 = teams[i][si]
                    s2 = teams[j][sj]

                    # Skip if neither student is conflicted
                    if s1 not in conflict and s2 not in conflict:
                        continue

                    before_score = (
                        team_score(teams[i], history) +
                        team_score(teams[j], history)
                    )
                    before_new = (
                        _new_pairs_in(teams[i], history) +
                        _new_pairs_in(teams[j], history)
                    )

                    # Tentative swap
                    teams[i][si], teams[j][sj] = s2, s1

                    after_score = (
                        team_score(teams[i], history) +
                        team_score(teams[j], history)
                    )
                    after_new = (
                        _new_pairs_in(teams[i], history) +
                        _new_pairs_in(teams[j], history)
                    )

                    if is_better(after_score, after_new, before_score, before_new):
                        improved = True  # keep the swap
                    else:
                        # Revert
                        teams[i][si], teams[j][sj] = s1, s2

    return teams


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _conflict_students(
    teams: list[list[str]],
    history: PairHistory,
) -> set[str]:
    """
    Set of students who share at least one prior pairing with a current teammate.
    These are the only students worth swapping — others are already clean.
    """
    conflict: set[str] = set()
    for team in teams:
        for s in team:
            if any(pair_score(s, t, history) > 0 for t in team if t != s):
                conflict.add(s)
    return conflict


def _new_pairs_in(team: list[str], history: PairHistory) -> int:
    """Count of never-met pairs within a single team."""
    return sum(
        1
        for a, b in combinations(team, 2)
        if history.get(pair_key(a, b)) is None
    )
