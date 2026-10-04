"""
fairness.py — Fairness enforcement pass.

FIX B2:  All has-met checks use has_met() — never pair_score > 0.
FIX B11: enforce() iterates to a fixpoint (up to max_passes) so a swap
          that fixes one student can't silently create a new violation.
"""

from __future__ import annotations

from algorithm.scorer import PairHistory, has_met


def enforce(
    teams: list[list[str]],
    history: PairHistory,
    max_passes: int = 10,
) -> list[list[str]]:
    """Iterate until no violations remain or no fix is possible."""
    for _ in range(max_passes):
        violations = _find_violations(teams, history)
        if not violations:
            break
        fixed_any = False
        for student, team_idx in violations:
            if _try_fix(student, team_idx, teams, history):
                fixed_any = True
        if not fixed_any:
            break
    return teams


def has_violations(teams: list[list[str]], history: PairHistory) -> list[str]:
    return [s for s, _ in _find_violations(teams, history)]


def _find_violations(
    teams: list[list[str]],
    history: PairHistory,
) -> list[tuple[str, int]]:
    violations = []
    for t_idx, team in enumerate(teams):
        for student in team:
            teammates = [m for m in team if m != student]
            if not teammates:
                continue
            if all(has_met(student, t, history) for t in teammates):
                violations.append((student, t_idx))
    return violations


def _try_fix(
    student: str,
    team_idx: int,
    teams: list[list[str]],
    history: PairHistory,
) -> bool:
    current_team = teams[team_idx]

    for other_idx, other_team in enumerate(teams):
        if other_idx == team_idx:
            continue

        for oj, candidate in enumerate(other_team):
            if has_met(student, candidate, history):
                continue

            for si, swap_out in enumerate(current_team):
                if swap_out == student:
                    continue

                current_team[si] = candidate
                other_team[oj] = swap_out

                student_fixed = any(
                    not has_met(student, m, history)
                    for m in current_team if m != student
                )
                candidate_ok = any(
                    not has_met(candidate, m, history)
                    for m in current_team if m != candidate
                )

                if student_fixed and candidate_ok:
                    return True

                current_team[si] = swap_out
                other_team[oj] = candidate

    return False
