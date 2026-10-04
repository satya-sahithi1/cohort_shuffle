"""
engine.py — Main entry point for the team formation algorithm.

This is the only function the formation service needs to call:

    result = engine.form_teams(students, team_size, history, locks)

Internally it orchestrates:
  1. Random assignment (first activity — no history)
  2. Greedy placement with time-limited restarts
  3. Swap optimisation
  4. Fairness pass
  5. Lock constraint application

Returns a FormationResult with teams, score, new_pairs, saturation,
and a list of students who still have no new teammate (if any — only
possible when the cohort is fully exhausted).
"""

from __future__ import annotations
import random
import time
from dataclasses import dataclass, field
from copy import deepcopy

from algorithm.scorer import (
    PairHistory,
    arrangement_score,
    count_new_pairs,
    saturation as compute_saturation,
    is_better,
)
from algorithm.greedy import place
from algorithm.swapper import optimise as swap_optimise
from algorithm.fairness import enforce as fairness_enforce, has_violations


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

@dataclass
class Lock:
    """
    A constraint between two students.
    constraint_type: 'together' | 'apart'
    """
    student_a: str
    student_b: str
    constraint_type: str  # 'together' or 'apart'


@dataclass
class FormationResult:
    teams: list[list[str]]
    score: int
    new_pairs: int
    saturation: float
    restarts: int
    elapsed_seconds: float
    unfair_students: list[str] = field(default_factory=list)
    # Students who have no new teammate (only non-empty when cohort is exhausted)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def form_teams(
    students: list[str],
    team_size: int,
    history: PairHistory,
    locks: list[Lock] | None = None,
    time_limit: float = 2.0,
    seed: int | None = None,
) -> FormationResult:
    """
    Form teams for one activity.

    Args:
        students   : list of student IDs registered for this activity
        team_size  : target team size
        history    : sparse pair history {(a,b): (count, days_ago)}
        locks      : optional list of together/apart constraints
        time_limit : seconds budget for restarts (default 2s)
        seed       : optional fixed seed for reproducible results (testing)

    Returns:
        FormationResult
    """
    if not students:
        return FormationResult(
            teams=[], score=0, new_pairs=0,
            saturation=0.0, restarts=0, elapsed_seconds=0.0,
        )

    locks = locks or []
    rng = random.Random(seed)
    start = time.monotonic()

    # ------------------------------------------------------------------
    # Stage 1: No history → pure random, done immediately
    # ------------------------------------------------------------------
    if not history:
        teams = place(students, team_size, history, rng)
        teams = _apply_locks(teams, locks)
        elapsed = time.monotonic() - start
        return FormationResult(
            teams=teams,
            score=0,
            new_pairs=count_new_pairs(teams, history),
            saturation=0.0,
            restarts=0,
            elapsed_seconds=elapsed,
        )

    # ------------------------------------------------------------------
    # Stage 2: History exists — greedy + swap with time-limited restarts
    # ------------------------------------------------------------------
    best_teams = place(students, team_size, history, rng)
    best_teams = swap_optimise(best_teams, history)
    best_teams = _apply_locks(best_teams, locks)
    best_score = arrangement_score(best_teams, history)
    best_new = count_new_pairs(best_teams, history)
    restarts = 0

    while time.monotonic() - start < time_limit:
        if best_score == 0:
            break  # perfect result, no point continuing

        candidate = place(students, team_size, history, rng)
        candidate = swap_optimise(candidate, history)
        candidate = _apply_locks(candidate, locks)
        c_score = arrangement_score(candidate, history)
        c_new = count_new_pairs(candidate, history)

        if is_better(c_score, c_new, best_score, best_new):
            best_teams = candidate
            best_score = c_score
            best_new = c_new

        restarts += 1

    # ------------------------------------------------------------------
    # Stage 3: Fairness pass — fix students with zero new teammates
    # ------------------------------------------------------------------
    best_teams = fairness_enforce(best_teams, history)

    elapsed = time.monotonic() - start
    sat = compute_saturation(history, len(students))
    unfair = has_violations(best_teams, history)

    return FormationResult(
        teams=best_teams,
        score=arrangement_score(best_teams, history),
        new_pairs=count_new_pairs(best_teams, history),
        saturation=sat,
        restarts=restarts,
        elapsed_seconds=elapsed,
        unfair_students=unfair,
    )


# ---------------------------------------------------------------------------
# Lock constraint application
# ---------------------------------------------------------------------------

def validate_locks(
    locks: list[Lock],
    team_size: int,
) -> list[str]:
    """
    Check locks for obvious impossibilities before formation runs.
    Returns a list of human-readable error messages.
    Empty list = all locks are satisfiable (as far as we can tell statically).
    """
    errors = []

    # Group 'together' locks into clusters
    together_clusters = _together_clusters(locks)
    for cluster in together_clusters:
        if len(cluster) > team_size:
            errors.append(
                f"Lock error: students {sorted(cluster)} must be together "
                f"but their group ({len(cluster)}) exceeds team size ({team_size})."
            )

    # 'Apart' locks: a student can't be required to be apart from more
    # people than there are teams, but we can't compute that without
    # knowing the participant count — so we only catch trivial cases here.
    # Full validation happens in the formation service once we know n_teams.

    return errors


def _apply_locks(
    teams: list[list[str]],
    locks: list[Lock],
) -> list[list[str]]:
    """
    Enforce lock constraints on an already-formed arrangement by doing
    targeted swaps.

    'together' locks: ensure both students are on the same team.
    'apart' locks:    ensure both students are on different teams.

    This is a best-effort post-processing step. The formation service
    validates locks before calling form_teams, so truly unsatisfiable
    locks should never reach here.
    """
    if not locks:
        return teams

    # Build a fast lookup: student → team index
    def student_team(s: str) -> int | None:
        for i, t in enumerate(teams):
            if s in t:
                return i
        return None

    for lock in locks:
        a, b = lock.student_a, lock.student_b
        idx_a = student_team(a)
        idx_b = student_team(b)

        if idx_a is None or idx_b is None:
            continue  # student not registered for this activity

        if lock.constraint_type == "together":
            if idx_a != idx_b:
                # Move b to a's team by swapping b with someone on a's team
                # (pick the swap that changes the non-locked teams least)
                for si, swap_out in enumerate(teams[idx_a]):
                    if swap_out == a:
                        continue
                    idx_b2 = student_team(b)
                    if idx_b2 is None:
                        break
                    b_pos = teams[idx_b2].index(b)
                    teams[idx_a][si], teams[idx_b2][b_pos] = b, swap_out
                    break

        elif lock.constraint_type == "apart":
            if idx_a == idx_b:
                # Move b to a different team — pick any other team
                for other_idx, other_team in enumerate(teams):
                    if other_idx == idx_a:
                        continue
                    b_pos = teams[idx_a].index(b)
                    # Swap b with anyone on other_team
                    teams[idx_a][b_pos], teams[other_idx][0] = (
                        teams[other_idx][0],
                        b,
                    )
                    break

    return teams


def _together_clusters(locks: list[Lock]) -> list[set[str]]:
    """
    Union-find to group students connected by 'together' locks.
    Used for static validation.
    """
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: str, y: str) -> None:
        parent[find(x)] = find(y)

    for lock in locks:
        if lock.constraint_type == "together":
            union(lock.student_a, lock.student_b)

    clusters: dict[str, set[str]] = {}
    for student in parent:
        root = find(student)
        clusters.setdefault(root, set()).add(student)

    return list(clusters.values())
