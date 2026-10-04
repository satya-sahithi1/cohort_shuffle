"""
swapper.py — Local swap optimisation.

FIX B2: _conflict_students and _new_pairs_in now use has_met() exclusively.
"""

from __future__ import annotations
from itertools import combinations

from algorithm.scorer import PairHistory, team_score, pair_score, pair_key, is_better, has_met


def optimise(teams: list[list[str]], history: PairHistory) -> list[list[str]]:
    if len(teams) < 2:
        return teams

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

                    if s1 not in conflict and s2 not in conflict:
                        continue

                    before_score = team_score(teams[i], history) + team_score(teams[j], history)
                    before_new = _new_pairs_in(teams[i], history) + _new_pairs_in(teams[j], history)

                    teams[i][si], teams[j][sj] = s2, s1

                    after_score = team_score(teams[i], history) + team_score(teams[j], history)
                    after_new = _new_pairs_in(teams[i], history) + _new_pairs_in(teams[j], history)

                    if is_better(after_score, after_new, before_score, before_new):
                        improved = True
                    else:
                        teams[i][si], teams[j][sj] = s1, s2

    return teams


def _conflict_students(teams: list[list[str]], history: PairHistory) -> set[str]:
    """FIX B2: use has_met instead of pair_score > 0."""
    conflict: set[str] = set()
    for team in teams:
        for s in team:
            if any(has_met(s, t, history) for t in team if t != s):
                conflict.add(s)
    return conflict


def _new_pairs_in(team: list[str], history: PairHistory) -> int:
    """FIX B2: use has_met instead of key lookup."""
    return sum(1 for a, b in combinations(team, 2) if not has_met(a, b, history))
