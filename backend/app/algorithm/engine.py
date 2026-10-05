"""
engine.py — Main entry point for the team formation algorithm.

Public API: form_teams()

Pipeline (from spec):
  1. Validate inputs and locks.
  2. If no history → shuffle randomly, apply locks, return.
  3. Compute locked-together clusters.
  4. Time-limited restart loop:
       a. place() — greedy with locked clusters pre-placed
       b. optimise() — swap improvement with deadline
       c. Keep best result seen so far.
       d. Early exit if cost == 0 (perfect result).
  5. Fairness pass on best result.
  6. Return FormationResult with seed, score, repeats, saturation, etc.

Lock handling:
  - together locks: students must be on the same team.
  - apart locks: students must be on different teams.
  - Validated up front; unsatisfied locks are reported, not silently dropped.
  - Locks naming unregistered students are reported in skipped_locks.
"""

from __future__ import annotations
import random
import time
from dataclasses import dataclass, field
from itertools import combinations

from app.algorithm.scorer import (
    PairHistory,
    arrangement_cost,
    count_repeat_pairs,
    fairness_cost,
    saturation as compute_saturation,
    is_better,
    has_met,
    total_cost,
)
from app.algorithm.shape import compute_shape
from app.algorithm.placer import place
from app.algorithm.swapper import optimise as swap_optimise


# ── Public types ──────────────────────────────────────────────────────────────

@dataclass
class Lock:
    """A constraint between two students for one activity."""
    student_a: str
    student_b: str
    constraint_type: str  # 'together' or 'apart'

    def __post_init__(self) -> None:
        if self.constraint_type not in ("together", "apart"):
            raise ValueError(
                f"constraint_type must be 'together' or 'apart', "
                f"got {self.constraint_type!r}"
            )


@dataclass
class FormationResult:
    teams: list[list[str]]
    score: float               # total arrangement cost (lower = better)
    repeat_pairs: int          # pairs that had met before
    saturation: float          # fraction of possible pairs used
    restarts: int              # number of random restarts performed
    elapsed_seconds: float
    random_seed: int           # seed used — store this to reproduce the result
    unfair_students: list[str] = field(default_factory=list)
    unsatisfied_locks: list[Lock] = field(default_factory=list)
    skipped_locks: list[Lock] = field(default_factory=list)


# ── Public API ────────────────────────────────────────────────────────────────

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
        students:   list of student IDs registered for this activity.
        team_size:  target team size (admin-set).
        history:    sparse pair history {(a,b): (count, days_since_last)}.
        locks:      together/apart constraints set by admin.
        time_limit: seconds budget for the restart loop.
        seed:       random seed; if None, one is chosen and stored in result.

    Raises:
        ValueError: team_size < 1 or duplicate student IDs.
    """
    # ── Input validation ──────────────────────────────────────────────────
    if team_size < 1:
        raise ValueError(f"team_size must be >= 1, got {team_size}")
    if len(students) != len(set(students)):
        dupes = sorted({s for s in students if students.count(s) > 1})
        raise ValueError(f"Duplicate student IDs: {dupes}")

    locks = locks or []

    # Choose and record seed
    if seed is None:
        seed = random.randrange(2 ** 32)
    rng = random.Random(seed)

    start = time.monotonic()
    deadline = start + time_limit

    # ── Separate locks for unregistered students ──────────────────────────
    student_set = set(students)
    active_locks: list[Lock] = []
    skipped_locks: list[Lock] = []
    for lock in locks:
        if lock.student_a in student_set and lock.student_b in student_set:
            active_locks.append(lock)
        else:
            skipped_locks.append(lock)

    # ── Validate locks ────────────────────────────────────────────────────
    n = len(students)
    shape = compute_shape(n, team_size)
    errors = validate_locks(active_locks, team_size, n_students=n, n_teams=shape.total_teams)
    if errors:
        return FormationResult(
            teams=[], score=0.0, repeat_pairs=0, saturation=0.0,
            restarts=0, elapsed_seconds=time.monotonic() - start,
            random_seed=seed,
            unsatisfied_locks=active_locks,
            skipped_locks=skipped_locks,
        )

    # ── Empty student list ────────────────────────────────────────────────
    if n == 0:
        return FormationResult(
            teams=[], score=0.0, repeat_pairs=0, saturation=0.0,
            restarts=0, elapsed_seconds=0.0, random_seed=seed,
        )

    # ── Extract together clusters for placer ─────────────────────────────
    together_clusters = _together_clusters(active_locks)

    # ── No history → random shuffle + apply locks ─────────────────────────
    if not history:
        shuffled = list(students)
        rng.shuffle(shuffled)
        teams = place(shuffled, team_size, history, together_clusters, rng)
        teams, unsatisfied = _apply_apart_locks(teams, active_locks)
        elapsed = time.monotonic() - start
        return FormationResult(
            teams=teams, score=0.0,
            repeat_pairs=0,
            saturation=0.0,
            restarts=0,
            elapsed_seconds=elapsed,
            random_seed=seed,
            unsatisfied_locks=unsatisfied,
            skipped_locks=skipped_locks,
        )

    # ── Time-limited restart loop ─────────────────────────────────────────
    best_teams = _one_pass(students, team_size, history, together_clusters, rng, deadline)
    best_cost = total_cost(best_teams, history, students)
    best_repeats = count_repeat_pairs(best_teams, history)
    restarts = 0

    if best_cost > 0:
        while time.monotonic() < deadline:
            candidate = _one_pass(students, team_size, history, together_clusters, rng, deadline)
            c_cost = total_cost(candidate, history, students)
            c_repeats = count_repeat_pairs(candidate, history)

            if is_better(c_cost, c_repeats, best_cost, best_repeats):
                best_teams = candidate
                best_cost = c_cost
                best_repeats = c_repeats

            restarts += 1

            if best_cost == 0:
                break  # perfect result — stop early

    # ── Fairness pass (after restarts, before reporting) ─────────────────
    best_teams = _fairness_pass(best_teams, history, students)

    # ── Apply apart locks ─────────────────────────────────────────────────
    best_teams, unsatisfied = _apply_apart_locks(best_teams, active_locks)

    elapsed = time.monotonic() - start
    sat = compute_saturation(history, students)
    unfair = _find_unfair(best_teams, history, students)

    return FormationResult(
        teams=best_teams,
        score=arrangement_cost(best_teams, history),
        repeat_pairs=count_repeat_pairs(best_teams, history),
        saturation=sat,
        restarts=restarts,
        elapsed_seconds=elapsed,
        random_seed=seed,
        unfair_students=unfair,
        unsatisfied_locks=unsatisfied,
        skipped_locks=skipped_locks,
    )


# ── Internal helpers ──────────────────────────────────────────────────────────

def _one_pass(
    students: list[str],
    team_size: int,
    history: PairHistory,
    together_clusters: list[list[str]],
    rng: random.Random,
    deadline: float,
) -> list[list[str]]:
    """One placement + swap cycle."""
    teams = place(students, team_size, history, together_clusters, rng)
    teams = swap_optimise(teams, history, students, deadline=deadline)
    return teams


def _fairness_pass(
    teams: list[list[str]],
    history: PairHistory,
    all_students: list[str],
) -> list[list[str]]:
    """
    Try to fix students who have no new teammate by swapping with someone
    from another team. Runs to a fixpoint (max 10 passes).
    """
    for _ in range(10):
        violations = _find_unfair_with_idx(teams, history, all_students)
        if not violations:
            break
        fixed_any = False
        for student, t_idx in violations:
            if _fix_unfair(student, t_idx, teams, history):
                fixed_any = True
        if not fixed_any:
            break
    return teams


def _fix_unfair(
    student: str,
    t_idx: int,
    teams: list[list[str]],
    history: PairHistory,
) -> bool:
    """
    Try to swap student with someone from another team who has never met them.
    Only accept if it doesn't create a new violation for the swapped-in student.
    """
    current_team = teams[t_idx]

    for other_idx, other_team in enumerate(teams):
        if other_idx == t_idx:
            continue
        for oj, candidate in enumerate(other_team):
            if has_met(student, candidate, history):
                continue  # candidate is not new to student

            for si, swap_out in enumerate(current_team):
                if swap_out == student:
                    continue
                # Try the swap
                current_team[si] = candidate
                other_team[oj] = swap_out

                student_fixed = any(
                    not has_met(student, m, history)
                    for m in current_team if m != student
                )
                candidate_ok = not all(
                    has_met(candidate, m, history)
                    for m in current_team if m != candidate
                )

                if student_fixed and candidate_ok:
                    return True

                # Revert
                current_team[si] = swap_out
                other_team[oj] = candidate

    return False


def _find_unfair(
    teams: list[list[str]],
    history: PairHistory,
    all_students: list[str],
) -> list[str]:
    return [s for s, _ in _find_unfair_with_idx(teams, history, all_students)]


def _find_unfair_with_idx(
    teams: list[list[str]],
    history: PairHistory,
    all_students: list[str],
) -> list[tuple[str, int]]:
    all_set = set(all_students)
    violations = []
    for t_idx, team in enumerate(teams):
        for student in team:
            teammates = [m for m in team if m != student]
            if not teammates:
                continue
            if all(has_met(student, t, history) for t in teammates):
                has_new_available = any(
                    not has_met(student, s, history)
                    for s in all_set if s != student
                )
                if has_new_available:
                    violations.append((student, t_idx))
    return violations


def _apply_apart_locks(
    teams: list[list[str]],
    locks: list[Lock],
) -> tuple[list[list[str]], list[Lock]]:
    """
    For each 'apart' lock where a and b are on the same team,
    move b to the team with fewest members.
    Returns (teams, list_of_still_unsatisfied_locks).
    """
    apart_locks = [l for l in locks if l.constraint_type == "apart"]
    for _ in range(5):  # iterate to handle chains
        unsatisfied = []
        for lock in apart_locks:
            a, b = lock.student_a, lock.student_b
            idx_a = _team_of(a, teams)
            idx_b = _team_of(b, teams)
            if idx_a is None or idx_b is None:
                continue
            if idx_a == idx_b:
                # Move b to smallest other team
                target = min(
                    (i for i in range(len(teams)) if i != idx_a),
                    key=lambda i: len(teams[i]),
                    default=None,
                )
                if target is not None:
                    teams[idx_a].remove(b)
                    teams[target].append(b)
                else:
                    unsatisfied.append(lock)
        # Re-check
        still = [
            l for l in apart_locks
            if _team_of(l.student_a, teams) == _team_of(l.student_b, teams)
            and _team_of(l.student_a, teams) is not None
        ]
        if not still:
            return teams, []
    return teams, still


def _team_of(student: str, teams: list[list[str]]) -> int | None:
    for i, team in enumerate(teams):
        if student in team:
            return i
    return None


# ── Lock validation ───────────────────────────────────────────────────────────

def validate_locks(
    locks: list[Lock],
    team_size: int,
    n_students: int = 0,
    n_teams: int = 0,
) -> list[str]:
    """
    Return error messages for unsatisfiable locks. Empty = all OK.

    Checks:
      1. Self-locks
      2. Together clusters larger than team_size
      3. Cluster-level contradictions (a+b together, b+c together, a+c apart)
      4. Apart locks when everyone fits on one team
      5. Apart-edge infeasibility (student must avoid more teams than exist)
    """
    errors: list[str] = []

    # 1. Self-locks
    for lock in locks:
        if lock.student_a == lock.student_b:
            errors.append(f"{lock.student_a!r} cannot be locked with themselves.")

    # Build together clusters
    clusters = _together_clusters(locks)
    student_to_cluster: dict[str, frozenset[str]] = {}
    for cluster in clusters:
        fs = frozenset(cluster)
        for s in cluster:
            student_to_cluster[s] = fs

    # 2. Together clusters larger than team_size
    for cluster in clusters:
        if len(cluster) > team_size:
            errors.append(
                f"Students {sorted(cluster)} must be together but their group "
                f"({len(cluster)}) exceeds team_size ({team_size})."
            )

    # 3. Cluster-level contradictions
    for lock in locks:
        if lock.constraint_type == "apart":
            a, b = lock.student_a, lock.student_b
            ca = student_to_cluster.get(a, frozenset({a}))
            cb = student_to_cluster.get(b, frozenset({b}))
            if ca & cb:
                errors.append(
                    f"{a!r} and {b!r} must be apart but are connected "
                    f"through a 'together' chain — contradiction."
                )

    # 4. Apart when everyone fits on one team
    if n_students > 0 and n_students <= team_size:
        if any(l.constraint_type == "apart" for l in locks):
            errors.append(
                f"'apart' locks cannot be satisfied when all {n_students} "
                f"students fit on one team (team_size {team_size})."
            )

    # 5. Apart-edge infeasibility
    if n_teams > 0:
        apart_neighbours: dict[str, set[str]] = {}
        for lock in locks:
            if lock.constraint_type == "apart":
                apart_neighbours.setdefault(lock.student_a, set()).add(lock.student_b)
                apart_neighbours.setdefault(lock.student_b, set()).add(lock.student_a)
        for student, neighbours in apart_neighbours.items():
            if len(neighbours) >= n_teams:
                errors.append(
                    f"{student!r} must be apart from {len(neighbours)} students "
                    f"but there are only {n_teams} teams."
                )

    return errors


# ── Union-find for together clusters ─────────────────────────────────────────

def _together_clusters(locks: list[Lock]) -> list[list[str]]:
    """Return list of student groups connected by 'together' locks."""
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

    clusters: dict[str, list[str]] = {}
    for s in parent:
        root = find(s)
        clusters.setdefault(root, []).append(s)

    return list(clusters.values())
