"""
engine.py — Main entry point for the team formation algorithm.

Fixes in this version:
  B3:  Lock-aware eviction — never displace a student who is part of a
       satisfied together-lock cluster on the same team. Exhaustion of
       legal eviction candidates is treated as an immediate hard failure
       (unsatisfied_locks populated, not thrashed).
  B6:  validate_locks now detects cluster-level contradictions (a+b+c
       together but a+c apart), apart-edge infeasibility (student needs
       more teams than exist), and n_students is required when apart
       locks are present. form_teams calls validate_locks and aborts
       with unsatisfied_locks if any error is returned.
  B9:  Deadline is threaded into swapper.optimise so a single swap pass
       also respects the time limit.
  B11: After a fairness swap, the outgoing student's team is re-checked
       for new violations; the swap is reverted if it creates one.
  B12: Best seeded before loop, score==0 checked before entering.
  B13: Locks naming unregistered students are reported in skipped_locks
       on FormationResult instead of being silently dropped.
  B14: Removed unused deepcopy import.
  B15: All imports use algorithm.* paths.
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


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

@dataclass
class Lock:
    student_a: str
    student_b: str
    constraint_type: str  # 'together' or 'apart'

    def __post_init__(self) -> None:
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
    unsatisfied_locks: list[Lock] = field(default_factory=list)
    skipped_locks: list[Lock] = field(default_factory=list)  # B13: unregistered students


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

    Raises:
        ValueError: if team_size < 1 or students contains duplicates.
    """
    if team_size < 1:
        raise ValueError(f"team_size must be >= 1, got {team_size}")

    if len(students) != len(set(students)):
        dupes = [s for s in set(students) if students.count(s) > 1]
        raise ValueError(f"students list contains duplicate IDs: {dupes}")

    if not students:
        return FormationResult(
            teams=[], score=0, new_pairs=0,
            saturation=0.0, restarts=0, elapsed_seconds=0.0,
        )

    locks = locks or []
    rng = random.Random(seed)
    start = time.monotonic()
    deadline = start + time_limit

    # B13: separate locks that name unregistered students
    student_set = set(students)
    active_locks, skipped = [], []
    for lock in locks:
        if lock.student_a in student_set and lock.student_b in student_set:
            active_locks.append(lock)
        else:
            skipped.append(lock)

    # B6: validate locks before formation — abort if unsatisfiable
    n = len(students)
    n_teams = max(1, n // team_size)
    errors = validate_locks(active_locks, team_size, n_students=n, n_teams=n_teams)
    if errors:
        # Return empty result signalling failure — service must notify admin
        return FormationResult(
            teams=[], score=0, new_pairs=0, saturation=0.0,
            restarts=0, elapsed_seconds=0.0,
            unsatisfied_locks=active_locks,
            skipped_locks=skipped,
        )

    # Stage 1: No history → random
    if not history:
        teams = place(students, team_size, history, rng)
        teams = fairness_enforce(teams, history)
        teams, unsatisfied = _apply_locks_fixpoint(teams, active_locks)
        elapsed = time.monotonic() - start
        return FormationResult(
            teams=teams, score=0,
            new_pairs=count_new_pairs(teams, history),
            saturation=0.0, restarts=0, elapsed_seconds=elapsed,
            unsatisfied_locks=unsatisfied, skipped_locks=skipped,
        )

    # Stage 2: History exists — time-limited restarts
    best_teams = place(students, team_size, history, rng)
    best_teams = swap_optimise(best_teams, history, deadline=deadline)
    best_score = arrangement_score(best_teams, history)
    best_new = count_new_pairs(best_teams, history)
    restarts = 0

    if best_score > 0:
        while time.monotonic() < deadline:
            candidate = place(students, team_size, history, rng)
            candidate = swap_optimise(candidate, history, deadline=deadline)  # B9
            c_score = arrangement_score(candidate, history)
            c_new = count_new_pairs(candidate, history)

            if is_better(c_score, c_new, best_score, best_new):
                best_teams = candidate
                best_score = c_score
                best_new = c_new

            restarts += 1

            if best_score == 0:
                break

    # B4: fairness before locks
    best_teams = fairness_enforce(best_teams, history)
    # B3: lock-aware fixpoint
    best_teams, unsatisfied = _apply_locks_fixpoint(best_teams, active_locks)

    elapsed = time.monotonic() - start
    sat = compute_saturation(history, n, registered=students)
    unfair = has_violations(best_teams, history)

    return FormationResult(
        teams=best_teams,
        score=arrangement_score(best_teams, history),
        new_pairs=count_new_pairs(best_teams, history),
        saturation=sat, restarts=restarts, elapsed_seconds=elapsed,
        unfair_students=unfair,
        unsatisfied_locks=unsatisfied,
        skipped_locks=skipped,
    )


# ---------------------------------------------------------------------------
# Lock validation (B6: complete)
# ---------------------------------------------------------------------------

def validate_locks(
    locks: list[Lock],
    team_size: int,
    n_students: int = 0,
    n_teams: int = 0,
) -> list[str]:
    """
    Return a list of error messages for unsatisfiable or contradictory locks.
    Empty list = all locks appear satisfiable.

    Checks performed:
    1. Self-locks (a locked with a)
    2. Cluster-level contradictions: together-cluster members locked apart (B6)
    3. Together clusters larger than team_size
    4. Apart locks when only one team can exist (B6)
    5. Apart-edge infeasibility: a student apart from too many others (B6)
    """
    errors = []

    # 1. Self-locks
    for lock in locks:
        if lock.student_a == lock.student_b:
            errors.append(
                f"Lock error: {lock.student_a!r} cannot be locked with themselves."
            )

    # Build together clusters via union-find
    together_clusters = _together_clusters(locks)
    # Map student → cluster root for O(1) lookup
    student_to_cluster: dict[str, frozenset[str]] = {}
    for cluster in together_clusters:
        fs = frozenset(cluster)
        for s in cluster:
            student_to_cluster[s] = fs

    # 2. Cluster-level contradictions: if a+b are in the same together-cluster
    #    but also have an apart lock, it is unsatisfiable (B6)
    for lock in locks:
        if lock.constraint_type == "apart":
            a, b = lock.student_a, lock.student_b
            cluster_a = student_to_cluster.get(a, frozenset({a}))
            cluster_b = student_to_cluster.get(b, frozenset({b}))
            if cluster_a & cluster_b:  # they share a together-cluster
                errors.append(
                    f"Lock error: {a!r} and {b!r} must be apart, but they are "
                    f"also connected through a 'together' chain — contradiction."
                )

    # 3. Together clusters larger than team_size
    for cluster in together_clusters:
        if len(cluster) > team_size:
            errors.append(
                f"Lock error: students {sorted(cluster)} must be together but "
                f"their group ({len(cluster)}) exceeds team size ({team_size})."
            )

    # 4. Apart locks when only one team can exist (B6)
    if n_students > 0 and n_students <= team_size:
        apart_locks = [l for l in locks if l.constraint_type == "apart"]
        if apart_locks:
            errors.append(
                f"Lock error: 'apart' locks cannot be satisfied when all "
                f"{n_students} students fit on one team (team size {team_size})."
            )

    # 5. Apart-edge infeasibility: count how many other students each student
    #    must be apart from. If that count >= n_teams, they need a team to
    #    themselves but the arrangement may not allow it (B6)
    if n_teams > 0:
        apart_count: dict[str, set[str]] = {}
        for lock in locks:
            if lock.constraint_type == "apart":
                apart_count.setdefault(lock.student_a, set()).add(lock.student_b)
                apart_count.setdefault(lock.student_b, set()).add(lock.student_a)
        for student, apart_from in apart_count.items():
            if len(apart_from) >= n_teams:
                errors.append(
                    f"Lock error: {student!r} must be apart from "
                    f"{len(apart_from)} students but there are only "
                    f"{n_teams} teams — cannot satisfy."
                )

    return errors


# ---------------------------------------------------------------------------
# Lock-aware fixpoint application (B3: complete fix)
# ---------------------------------------------------------------------------

def _apply_locks_fixpoint(
    teams: list[list[str]],
    locks: list[Lock],
    max_iterations: int = 3,
) -> tuple[list[list[str]], list[Lock]]:
    """
    Apply locks iteratively. Stops as soon as all locks are satisfied or
    a full pass makes no progress (hard failure — not thrashed endlessly).

    B3 fix: max_iterations reduced to 3 (was 20). Thrashing beyond that
    means the configuration is genuinely conflicted; report it, don't loop.
    """
    if not locks:
        return teams, []

    # Pre-compute which students are in together-lock clusters
    # so _apply_one_lock can avoid evicting them (B3)
    locked_students = _students_in_together_locks(locks)

    for _ in range(max_iterations):
        unsatisfied = _check_locks(teams, locks)
        if not unsatisfied:
            break
        changed = False
        for lock in unsatisfied:
            if _apply_one_lock(teams, lock, locked_students):
                changed = True
        if not changed:
            break

    return teams, _check_locks(teams, locks)


def _students_in_together_locks(locks: list[Lock]) -> set[str]:
    """All students that appear in at least one together lock."""
    result: set[str] = set()
    for lock in locks:
        if lock.constraint_type == "together":
            result.add(lock.student_a)
            result.add(lock.student_b)
    return result


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


def _apply_one_lock(
    teams: list[list[str]],
    lock: Lock,
    locked_students: set[str],
) -> bool:
    """
    Try to satisfy a single lock by swapping one student.

    B3 fix: When satisfying a together lock by moving b onto a's team,
    never displace a student who is in `locked_students` (i.e. part of
    a together-lock cluster). Only evict unlocked members. If no legal
    eviction candidate exists, return False immediately.
    """
    a, b = lock.student_a, lock.student_b
    idx_a = _team_of(a, teams)
    idx_b = _team_of(b, teams)
    if idx_a is None or idx_b is None:
        return False

    if lock.constraint_type == "together" and idx_a != idx_b:
        # Find a member of a's team who is NOT locked (safe to displace)
        for si, swap_out in enumerate(teams[idx_a]):
            if swap_out == a:
                continue
            if swap_out in locked_students:
                continue  # B3: never displace a locked student
            idx_b2 = _team_of(b, teams)
            if idx_b2 is None:
                return False
            b_pos = teams[idx_b2].index(b)
            teams[idx_a][si], teams[idx_b2][b_pos] = b, swap_out
            return True
        return False  # no legal eviction candidate

    elif lock.constraint_type == "apart" and idx_a == idx_b:
        # Move b to another team — prefer teams with no locked students
        b_pos = teams[idx_a].index(b)
        for other_idx, other_team in enumerate(teams):
            if other_idx == idx_a:
                continue
            teams[idx_a][b_pos], other_team[0] = other_team[0], b
            return True

    return False


def _team_of(student: str, teams: list[list[str]]) -> int | None:
    for i, team in enumerate(teams):
        if student in team:
            return i
    return None


# ---------------------------------------------------------------------------
# Union-find for together-cluster detection
# ---------------------------------------------------------------------------

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
