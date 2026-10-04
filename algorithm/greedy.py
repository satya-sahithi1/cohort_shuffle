"""
greedy.py — Randomised greedy placement.

How it works:
1. Compute each student's overlap load (total conflict score vs all others).
2. Sort students by load descending + small random jitter.
   Most-conflicted students are placed first because they are hardest to fit.
   Jitter ensures different restarts produce different orderings.
3. Place each student into the team with the lowest marginal score that
   still has room.
4. Apply the remainder rule for leftover students.

Remainder rule:
    r = len(students) % team_size

    r == 0              → all teams exactly team_size
    r == 1              → absorb into existing (never create a solo team)
    r < team_size / 2   → absorb: distribute extras one-by-one into existing teams
    r > team_size / 2   → form one new smaller team with the extras
    r == team_size / 2  → form one new smaller team (boundary → new team)
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
    """
    One greedy placement pass. Returns a list of teams (list of lists).
    `rng` is an explicit Random instance so callers control the seed.
    """
    n = len(students)

    if n == 0:
        return []
    if n <= team_size:
        # Everyone on one team — matches the spec's "fewer than team_size" rule
        return [list(students)]

    r = n % team_size
    half = team_size / 2  # float intentional: handles both even and odd team_size

    if r == 0:
        num_teams = n // team_size
        absorb_count = 0
    elif r == 1 or r < half:
        # absorb case: grow some teams to team_size + 1
        num_teams = n // team_size
        absorb_count = r
    else:
        # new smaller team: r >= half (and r != 0 already handled above)
        num_teams = n // team_size + 1
        absorb_count = 0

    # Sort: most-conflicted first, jitter breaks ties randomly
    pool = sorted(
        students,
        key=lambda s: _overlap_load(s, students, history) + rng.uniform(0, 0.5),
        reverse=True,
    )

    if absorb_count:
        # The least-conflicted students are extras (end of sorted list)
        main_pool = pool[:-absorb_count]
        extras = pool[-absorb_count:]
    else:
        main_pool = pool
        extras = []

    teams: list[list[str]] = [[] for _ in range(num_teams)]

    # Place main pool
    for student in main_pool:
        idx = _best_team_idx(student, teams, team_size, history)
        teams[idx].append(student)

    # Absorb extras: each goes to the team with least marginal overlap
    for student in extras:
        idx = min(
            range(len(teams)),
            key=lambda i: marginal_score(student, teams[i], history),
        )
        teams[idx].append(student)

    return teams


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _overlap_load(student: str, all_students: list[str], history: PairHistory) -> int:
    """
    Total pair score for this student against every other registered student.
    Represents how 'conflicted' they are — high load means they've worked
    with many people already, so they're harder to place without repeats.
    """
    return sum(pair_score(student, o, history) for o in all_students if o != student)


def _best_team_idx(
    student: str,
    teams: list[list[str]],
    team_size: int,
    history: PairHistory,
) -> int:
    """
    Index of the team with the lowest marginal score for this student
    that still has an open slot (len < team_size).
    Falls back to the smallest team if all are full (shouldn't normally happen).
    """
    best_idx = None
    best_cost = float("inf")

    for i, team in enumerate(teams):
        if len(team) < team_size:
            cost = marginal_score(student, team, history)
            if cost < best_cost:
                best_cost = cost
                best_idx = i

    if best_idx is None:
        # Safety fallback: all teams full, pick smallest
        best_idx = min(range(len(teams)), key=lambda i: len(teams[i]))

    return best_idx
