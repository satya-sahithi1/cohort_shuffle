"""
swapper.py — Local swap improvement.

For each pair of teams, try swapping one student from each.
Keep the swap only if it strictly lowers total cost.

Rescore only the two touched teams (not all teams) — O(k) per swap
instead of O(n*k). This matches the spec requirement.

Stops when no improving swap is found or the time deadline is reached.
"""

from __future__ import annotations
import time
from itertools import combinations

from app.algorithm.scorer import PairHistory, team_cost, is_better, count_repeat_pairs


def optimise(
    teams: list[list[str]],
    history: PairHistory,
    all_students: list[str],
    deadline: float | None = None,
) -> list[list[str]]:
    """
    Improve teams by pairwise student swaps.

    deadline: monotonic time after which we stop mid-pass (from spec B9 fix).
    all_students: needed for fairness cost calculation.
    """
    if len(teams) < 2:
        return teams

    improved = True
    while improved:
        if deadline is not None and time.monotonic() > deadline:
            break
        improved = False

        for i, j in combinations(range(len(teams)), 2):
            if deadline is not None and time.monotonic() > deadline:
                break

            # Cache scores for the two teams before trying any swap
            score_i = team_cost(teams[i], history)
            score_j = team_cost(teams[j], history)
            before_cost = score_i + score_j
            before_repeats = _team_repeats(teams[i], history) + _team_repeats(teams[j], history)

            best_swap: tuple[int, int] | None = None
            best_cost = before_cost
            best_repeats = before_repeats

            for si in range(len(teams[i])):
                for sj in range(len(teams[j])):
                    # Try swap
                    teams[i][si], teams[j][sj] = teams[j][sj], teams[i][si]

                    after_cost = team_cost(teams[i], history) + team_cost(teams[j], history)
                    after_repeats = (
                        _team_repeats(teams[i], history)
                        + _team_repeats(teams[j], history)
                    )

                    if is_better(after_cost, after_repeats, best_cost, best_repeats):
                        best_cost = after_cost
                        best_repeats = after_repeats
                        best_swap = (si, sj)

                    # Always revert — we apply the best swap after scanning
                    teams[i][si], teams[j][sj] = teams[j][sj], teams[i][si]

            if best_swap is not None:
                si, sj = best_swap
                teams[i][si], teams[j][sj] = teams[j][sj], teams[i][si]
                improved = True

    return teams


def _team_repeats(team: list[str], history: PairHistory) -> int:
    """Count repeat pairs in a single team."""
    from app.algorithm.scorer import has_met
    from itertools import combinations as comb
    return sum(1 for a, b in comb(team, 2) if has_met(a, b, history))
