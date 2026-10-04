"""
fairness.py — Fairness enforcement pass.

After swap optimisation, check whether any student has zero new teammates
(everyone on their team is a repeat). This is the "real failure" condition
from the spec.

For each such student, find someone from another team they have never
worked with and try a targeted swap. The swap is kept if it fixes the
violation without creating a new one.

If a student is genuinely exhausted (has worked with every other
registered student), no fix is possible. The scoring function already
handles this via recency — no error is raised.
"""

from __future__ import annotations

from algorithm.scorer import PairHistory, pair_key, pair_score


def enforce(
    teams: list[list[str]],
    history: PairHistory,
) -> list[list[str]]:
    """
    Run the fairness pass on `teams`. Modifies in-place and returns.
    """
    violations = _find_violations(teams, history)
    if not violations:
        return teams

    for student, team_idx in violations:
        _try_fix(student, team_idx, teams, history)

    return teams


def has_violations(teams: list[list[str]], history: PairHistory) -> list[str]:
    """
    Return a list of students who have no new teammate on their team.
    Empty list = fairness constraint satisfied.
    """
    return [s for s, _ in _find_violations(teams, history)]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_violations(
    teams: list[list[str]],
    history: PairHistory,
) -> list[tuple[str, int]]:
    """
    Returns list of (student, team_index) for every student with no new teammate.
    """
    violations = []
    for t_idx, team in enumerate(teams):
        for student in team:
            teammates = [m for m in team if m != student]
            if not teammates:
                continue  # solo student — no teammates to evaluate
            all_repeats = all(pair_score(student, t, history) > 0 for t in teammates)
            if all_repeats:
                violations.append((student, t_idx))
    return violations


def _try_fix(
    student: str,
    team_idx: int,
    teams: list[list[str]],
    history: PairHistory,
) -> bool:
    """
    Try to swap a member of student's team with someone from another team
    that student has never worked with.

    Keeps the first swap that:
      1. Gives `student` at least one new teammate.
      2. Does not create a new violation for the swapped-in student.

    Returns True if a fix was found and applied.
    """
    current_team = teams[team_idx]

    for other_idx, other_team in enumerate(teams):
        if other_idx == team_idx:
            continue

        for oj, candidate in enumerate(other_team):
            # candidate must be someone student has never worked with
            if history.get(pair_key(student, candidate)) is not None:
                continue

            # Try swapping candidate with each member of student's team
            # (not student themselves)
            for si, swap_out in enumerate(current_team):
                if swap_out == student:
                    continue

                # Tentative swap
                current_team[si] = candidate
                other_team[oj] = swap_out

                # Check: does student now have at least one new teammate?
                student_fixed = any(
                    history.get(pair_key(student, m)) is None
                    for m in current_team if m != student
                )

                # Check: does candidate (now in current_team) have a new teammate?
                # We don't want to just move the violation to someone else.
                candidate_ok = any(
                    history.get(pair_key(candidate, m)) is None
                    for m in current_team if m != candidate
                )

                if student_fixed and candidate_ok:
                    return True  # keep swap

                # Revert
                current_team[si] = swap_out
                other_team[oj] = candidate

    return False  # no fix found (student may be exhausted)
