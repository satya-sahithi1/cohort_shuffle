"""
greedy.py — Randomised greedy placement.

FIX B5: Absorb-remainder now distributes each extra to a DIFFERENT team
         using a `grew` set, preventing all extras from landing on team 0
         when marginal scores are equal (empty history case).
"""

from __future__ import annotations
import random

from algorithm.scorer import PairHistory, marginal_score, pair_score


def place(
    students: list[str],
    team_size: int,
    history: PairHistory,
    rng: random.Random,
) -> list[list[str]]:
    n = len(students)

    if n == 0:
        return []
    if n <= team_size:
        return [list(students)]

    r = n % team_size
    half = team_size / 2

    if r == 0:
        num_teams = n // team_size
        absorb_count = 0
    elif r == 1 or r < half:
        num_teams = n // team_size
        absorb_count = r
    else:
        num_teams = n // team_size + 1
        absorb_count = 0

    pool = sorted(
        students,
        key=lambda s: _overlap_load(s, students, history) + rng.uniform(0, 0.5),
        reverse=True,
    )

    if absorb_count:
        main_pool = pool[:-absorb_count]
        extras = pool[-absorb_count:]
    else:
        main_pool = pool
        extras = []

    teams: list[list[str]] = [[] for _ in range(num_teams)]

    for student in main_pool:
        idx = _best_team_idx(student, teams, team_size, history)
        teams[idx].append(student)

    # FIX B5: track which teams already received an extra
    grew: set[int] = set()
    for student in extras:
        candidates = [i for i in range(len(teams)) if i not in grew]
        if not candidates:
            candidates = list(range(len(teams)))
        idx = min(candidates, key=lambda i: marginal_score(student, teams[i], history))
        teams[idx].append(student)
        grew.add(idx)

    return teams


def _overlap_load(student: str, all_students: list[str], history: PairHistory) -> int:
    return sum(pair_score(student, o, history) for o in all_students if o != student)


def _best_team_idx(
    student: str,
    teams: list[list[str]],
    team_size: int,
    history: PairHistory,
) -> int:
    best_idx = None
    best_cost = float("inf")

    for i, team in enumerate(teams):
        if len(team) < team_size:
            cost = marginal_score(student, team, history)
            if cost < best_cost:
                best_cost = cost
                best_idx = i

    if best_idx is None:
        best_idx = min(range(len(teams)), key=lambda i: len(teams[i]))

    return best_idx
