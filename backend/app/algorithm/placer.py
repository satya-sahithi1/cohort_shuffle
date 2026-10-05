"""
placer.py — Greedy team placement.

Steps (from spec):
  1. Work out team shape (delegated to shape.py).
  2. Place locked-together clusters first — each cluster goes into one team.
  3. Sort remaining students by "conflict load" descending (most-paired first)
     with a small random jitter so restarts explore different orderings.
  4. Assign each student greedily to the team with lowest marginal cost
     that still has room.
  5. Absorb remainder students one per team (distribute, not pile up).
"""

from __future__ import annotations
import random

from app.algorithm.scorer import PairHistory, marginal_cost, pair_cost
from app.algorithm.shape import TeamShape, compute_shape


def place(
    students: list[str],
    team_size: int,
    history: PairHistory,
    locks_together: list[list[str]],  # pre-validated together clusters
    rng: random.Random,
) -> list[list[str]]:
    """
    Place students into teams using greedy assignment.

    locks_together: list of student groups that must be on the same team.
    Each group has already been validated to fit within team_size.
    """
    n = len(students)
    if n == 0:
        return []

    shape = compute_shape(n, team_size)

    # Initialise empty teams according to shape
    # Absorb teams get +1 slot; small team gets small_size slots
    teams: list[list[str]] = []
    capacities: list[int] = []
    for i in range(shape.n_full_teams):
        teams.append([])
        capacities.append(shape.team_size + (1 if i < shape.absorb_count else 0))
    if shape.small_size > 0:
        teams.append([])
        capacities.append(shape.small_size)

    # ── Step 2: place locked-together clusters ────────────────────────────
    # Find teams with enough room for each cluster and assign.
    locked_placed: set[str] = set()
    for cluster in locks_together:
        cluster_size = len(cluster)
        placed = False
        for i, team in enumerate(teams):
            if len(team) + cluster_size <= capacities[i]:
                for s in cluster:
                    team.append(s)
                    locked_placed.add(s)
                placed = True
                break
        if not placed:
            # No single team fits — place as-is in the least-full team
            # (validate_locks should have caught oversized clusters, but be safe)
            idx = min(range(len(teams)), key=lambda i: len(teams[i]))
            for s in cluster:
                teams[idx].append(s)
                locked_placed.add(s)

    # ── Step 3: sort remaining students by conflict load + jitter ─────────
    remaining = [s for s in students if s not in locked_placed]
    remaining.sort(
        key=lambda s: _conflict_load(s, students, history) + rng.uniform(0.0, 0.5),
        reverse=True,
    )

    # ── Step 4: greedy assignment ─────────────────────────────────────────
    for student in remaining:
        idx = _best_team(student, teams, capacities, history)
        teams[idx].append(student)

    return teams


def _conflict_load(student: str, all_students: list[str], history: PairHistory) -> float:
    """Sum of pair costs with all other students — higher means more history."""
    return sum(pair_cost(student, o, history) for o in all_students if o != student)


def _best_team(
    student: str,
    teams: list[list[str]],
    capacities: list[int],
    history: PairHistory,
) -> int:
    """Return the index of the team with the lowest marginal cost that has room."""
    best_idx = 0
    best_cost = float("inf")

    for i, team in enumerate(teams):
        if len(team) < capacities[i]:
            cost = marginal_cost(student, team, history)
            if cost < best_cost:
                best_cost = cost
                best_idx = i

    return best_idx
