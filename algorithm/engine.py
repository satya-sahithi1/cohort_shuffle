"""
engine.py — Main entry point.

Fixes applied:
  B3:  Lock application uses fixpoint loop — never leaves locks silently unsatisfied
  B4:  Fairness runs BEFORE lock application
  B6:  validate_locks catches self-locks, contradictions, apart-when-one-team
  B7:  team_size < 1 raises ValueError
  B9:  Restart loop checks clock before each cycle
  B10: Duplicate student IDs raise ValueError
  B12: Best seeded before loop; score==0 checked before entering loop
  B13: Lock validates constraint_type in __post_init__; unsatisfied_locks in result
  B14: Removed unused deepcopy import
  B15: All imports use algorithm.* (not backend.algorithm.*)
"""

from __future__ import annotations
import random
import time
from dataclasses import dataclass, field

from algorithm.scorer import (
    PairHistory, arrangement_score, count_new_pairs,
    saturation as compute_saturation, is_better, has_met,
)
from algorithm.greedy import place
from algorithm.swapper import optimise as swap_optimise
from algorithm.fairness import enforce as fairness_enforce, has_violations


@dataclass
class Lock:
    student_a: str
    student_b: str
    constraint_type: str  # 'together' or 'apart'

    def __post_init__(self) -> None:
        # FIX B13
        if self.constraint_type not in ("together", "apart"):
            raise ValueError(
                f"Lock.constraint_type must be 'together' or 'apart', "
                f"got {self.constraint_type!r}"
            )


@dataclass
class FormationResult:
    teams: list[list[str]]
    score: int
    new_pairs: int
    saturation: float
    restarts: int
    elapsed_seconds: float
    unfair_students: list[str] = field(default_factory=list)
    unsatisfied_locks: list[Lock] = field(default_factory=list)  # FIX B13


def form_teams(
    students: list[str],
    team_size: int,
    history: PairHistory,
    locks: list[Lock] | None = None,
    time_limit: float = 2.0,
    seed: int | None = None,
) -> FormationResult:
    # FIX B7
    if team_size < 1:
        raise ValueError(f"team_size must be >= 1, got {team_size}")

    # FIX B10
    if len(students) != len(set(students)):
        dupes = [s for s in set(students) if students.count(s) > 1]
        raise ValueError(f"students list contains duplicate IDs: {dupes}")

    if not students:
        return FormationResult(teams=[], score=0, new_pairs=0,
                               saturation=0.0, restarts=0, elapsed_seconds=0.0)

    locks = locks or []
    rng = random.Random(seed)
    start = time.monotonic()

    if not history:
        teams = place(students, team_size, history, rng)
        teams = fairness_enforce(teams, history)           # FIX B4
        teams, unsatisfied = _apply_locks_fixpoint(teams, locks)  # FIX B3
        elapsed = time.monotonic() - start
        return FormationResult(
            teams=teams, score=0,
            new_pairs=count_new_pairs(teams, history),
            saturation=0.0, restarts=0, elapsed_seconds=elapsed,
            unsatisfied_locks=unsatisfied,
        )

    # FIX B12: seed best before loop, check score==0 before entering
    best_teams = place(students, team_size, history, rng)
    best_teams = swap_optimise(best_teams, history)
    best_score = arrangement_score(best_teams, history)
    best_new = count_new_pairs(best_teams, history)
    restarts = 0

    if best_score > 0:
        # FIX B9: check clock at top of each iteration
        while time.monotonic() - start < time_limit:
            candidate = place(students, team_size, history, rng)
            candidate = swap_optimise(candidate, history)
            c_score = arrangement_score(candidate, history)
            c_new = count_new_pairs(candidate, history)

            if is_better(c_score, c_new, best_score, best_new):
                best_teams = candidate
                best_score = c_score
                best_new = c_new

            restarts += 1

            if best_score == 0:
                break

    # FIX B4: fairness BEFORE locks
    best_teams = fairness_enforce(best_teams, history)
    # FIX B3: fixpoint lock application
    best_teams, unsatisfied = _apply_locks_fixpoint(best_teams, locks)

    elapsed = time.monotonic() - start
    sat = compute_saturation(history, len(students), registered=students)  # FIX B8
    unfair = has_violations(best_teams, history)

    return FormationResult(
        teams=best_teams,
        score=arrangement_score(best_teams, history),
        new_pairs=count_new_pairs(best_teams, history),
        saturation=sat, restarts=restarts, elapsed_seconds=elapsed,
        unfair_students=unfair, unsatisfied_locks=unsatisfied,
    )


def validate_locks(
    locks: list[Lock],
    team_size: int,
    n_students: int = 0,
) -> list[str]:
    """FIX B6: catches self-locks, contradictions, apart-when-one-team."""
    errors = []

    for lock in locks:
        if lock.student_a == lock.student_b:
            errors.append(
                f"Lock error: student {lock.student_a!r} cannot be locked with themselves."
            )

    together_pairs = {
        (min(l.student_a, l.student_b), max(l.student_a, l.student_b))
        for l in locks if l.constraint_type == "together"
    }
    apart_pairs = {
        (min(l.student_a, l.student_b), max(l.student_a, l.student_b))
        for l in locks if l.constraint_type == "apart"
    }
    for pair in together_pairs & apart_pairs:
        errors.append(
            f"Lock error: {pair[0]!r} and {pair[1]!r} are locked both "
            f"'together' and 'apart' — contradiction."
        )

    for cluster in _together_clusters(locks):
        if len(cluster) > team_size:
            errors.append(
                f"Lock error: students {sorted(cluster)} must be together "
                f"but their group ({len(cluster)}) exceeds team size ({team_size})."
            )

    if n_students > 0 and n_students <= team_size:
        apart_locks = [l for l in locks if l.constraint_type == "apart"]
        if apart_locks:
            errors.append(
                f"Lock error: 'apart' locks cannot be satisfied when all "
                f"{n_students} students fit on one team (team size {team_size})."
            )

    return errors


# ---------------------------------------------------------------------------
# Lock fixpoint application (FIX B3)
# ---------------------------------------------------------------------------

def _apply_locks_fixpoint(
    teams: list[list[str]],
    locks: list[Lock],
    max_iterations: int = 20,
) -> tuple[list[list[str]], list[Lock]]:
    if not locks:
        return teams, []

    for _ in range(max_iterations):
        unsatisfied = _check_locks(teams, locks)
        if not unsatisfied:
            break
        changed = False
        for lock in unsatisfied:
            if _apply_one_lock(teams, lock):
                changed = True
        if not changed:
            break

    return teams, _check_locks(teams, locks)


def _check_locks(teams: list[list[str]], locks: list[Lock]) -> list[Lock]:
    violated = []
    for lock in locks:
        a, b = lock.student_a, lock.student_b
        idx_a = _team_of(a, teams)
        idx_b = _team_of(b, teams)
        if idx_a is None or idx_b is None:
            continue
        if lock.constraint_type == "together" and idx_a != idx_b:
            violated.append(lock)
        elif lock.constraint_type == "apart" and idx_a == idx_b:
            violated.append(lock)
    return violated


def _apply_one_lock(teams: list[list[str]], lock: Lock) -> bool:
    a, b = lock.student_a, lock.student_b
    idx_a = _team_of(a, teams)
    idx_b = _team_of(b, teams)
    if idx_a is None or idx_b is None:
        return False

    if lock.constraint_type == "together" and idx_a != idx_b:
        for si, swap_out in enumerate(teams[idx_a]):
            if swap_out == a:
                continue
            idx_b2 = _team_of(b, teams)
            if idx_b2 is None:
                return False
            b_pos = teams[idx_b2].index(b)
            teams[idx_a][si], teams[idx_b2][b_pos] = b, swap_out
            return True

    elif lock.constraint_type == "apart" and idx_a == idx_b:
        for other_idx, other_team in enumerate(teams):
            if other_idx == idx_a:
                continue
            b_pos = teams[idx_a].index(b)
            teams[idx_a][b_pos], other_team[0] = other_team[0], b
            return True

    return False


def _team_of(student: str, teams: list[list[str]]) -> int | None:
    for i, team in enumerate(teams):
        if student in team:
            return i
    return None


def _together_clusters(locks: list[Lock]) -> list[set[str]]:
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
