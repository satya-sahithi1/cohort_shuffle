"""
Greedy placement step.

Students are sorted by their overlap load (most conflicted first)
with a small random jitter so repeated runs produce different arrangements.
Each student is placed into the team with the lowest marginal score.
The remainder rule is applied after all main placements.
"""

from __future__ import annotations
import random
from typing import TYPE_CHECKING

from .scorer import marginal_score, pair_score

if TYPE_CHECKING:
    from .engine import PairHistory


def overlap_load(student: str, others: list[str], pair_history: "PairHistory") -> int:
    """
    Total overlap score of this student against all other registered students.
    Used to decide placement order: most-conflicted students go first.
    """
    return sum(pair_score(student, o, pair_history) for o in others if o != student)


def place(
    students: list[str],
    team_size: int,
    pair_history: "PairHistory",
    rng: random.Random,
) -> list[list[str]]:
    """
    Single greedy placement pass.

    Returns a list of teams. Team sizes follow the remainder rule:
      r = len(students) % team_size
      r == 0                → all teams exactly team_size
      r == 1                → absorb into existing (never a solo team)
      r <= team_size // 2   → absorb into existing teams (they grow to team_size+1)
      r >  team_size // 2   → form one extra smaller team
      r == team_size / 2 exactly (even team_size) → new smaller team
    """
    n = len(students)

    if n == 0:
        return []
    if n <= team_size:
        return [students[:]]

    r = n % team_size
    half = team_size / 2  # intentional float for boundary comparison

    if r == 0:
        num_teams = n // team_size
        absorb_count = 0
    elif r == 1 or r < half:
        # absorb: distribute extras into existing teams
        num_teams = n // team_size
        absorb_count = r
    else:
        # new smaller team (r > half, including r == half for even team_size)
        num_teams = n // team_size + 1
        absorb_count = 0

    # Sort by overlap load descending + jitter so repeated calls differ
    pool = sorted(
        students,
        key=lambda s: overlap_load(s, students, pair_history) + rng.uniform(0, 0.5),
        reverse=True,
    )

    # Split into main pool and leftovers for absorb case
    if absorb_count:
        # Take the last absorb_count students as extras (lowest conflict score)
        main_pool = pool[:-absorb_count]
        extras = pool[-absorb_count:]
    else:
        main_pool = pool
        extras = []

    teams: list[list[str]] = [[] for _ in range(num_teams)]

    # Greedy placement: each student goes to the team with lowest marginal cost
    for student in main_pool:
        best_idx = _best_team(student, teams, team_size, pair_history)
        teams[best_idx].append(student)

    # Absorb extras into the teams with the least overlap with each extra student
    for student in extras:
        best_idx = min(
            range(len(teams)),
            key=lambda i: marginal_score(student, teams[i], pair_history),
        )
        teams[best_idx].append(student)

    return teams


def _best_team(
    student: str,
    teams: list[list[str]],
    team_size: int,
    pair_history: "PairHistory",
) -> int:
    """
    Index of the team with the lowest marginal cost for this student
    that still has room (len < team_size).
    Falls back to the smallest team if all are full.
    """
    best_idx = None
    best_cost = float("inf")

    for i, team in enumerate(teams):
        if len(team) < team_size:
            cost = marginal_score(student, team, pair_history)
            if cost < best_cost:
                best_cost = cost
                best_idx = i

    if best_idx is None:
        # All teams are at capacity — pick smallest (absorb overflow)
        best_idx = min(range(len(teams)), key=lambda i: len(teams[i]))

    return best_idx
