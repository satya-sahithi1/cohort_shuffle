"""
shape.py — Team shape calculation.

Rules (from spec):
  Let n = number of students, k = team_size, r = n % k

  1. n < k          → one team of n  (never refuse to form)
  2. r == 0         → n//k full teams of size k
  3. r >= k/2 AND r >= 2 → (n//k) full teams + one smaller team of r
  4. otherwise      → (n//k) full teams, remainder absorbed into existing
                       teams (those become size k+1). r extras distributed
                       one per team, starting from team 0.

  Never create a team of 1.

  Returns a TeamShape with:
    n_full_teams   — number of teams of size k
    small_size     — size of the extra small team (0 if none)
    absorb_count   — number of extras distributed into full teams
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class TeamShape:
    n_full_teams: int    # teams of exactly team_size
    small_size: int      # size of the extra small team (0 = no small team)
    absorb_count: int    # extras absorbed into full teams (one each)
    team_size: int       # original requested team size
    n_students: int      # total students

    @property
    def total_teams(self) -> int:
        return self.n_full_teams + (1 if self.small_size > 0 else 0)

    @property
    def sizes(self) -> list[int]:
        """List of all team sizes in this arrangement."""
        result = []
        for i in range(self.n_full_teams):
            # Each of the first absorb_count teams gets one extra student.
            # If absorb_count > n_full_teams, distribute floor then remainder.
            per_team, leftover = divmod(self.absorb_count, self.n_full_teams) if self.n_full_teams else (0, 0)
            extra = per_team + (1 if i < leftover else 0)
            result.append(self.team_size + extra)
        if self.small_size > 0:
            result.append(self.small_size)
        return result


def compute_shape(n_students: int, team_size: int) -> TeamShape:
    """
    Compute the team shape for n_students students and a target team_size.

    >>> compute_shape(12, 4)   # 3 full teams, no remainder
    TeamShape(n_full_teams=3, small_size=0, absorb_count=0, ...)
    >>> compute_shape(14, 4)   # r=2, r >= 4/2 → new small team of 2
    TeamShape(n_full_teams=3, small_size=2, absorb_count=0, ...)
    >>> compute_shape(13, 4)   # r=1 → absorb into 3 full teams (1 becomes size 5)
    TeamShape(n_full_teams=3, small_size=0, absorb_count=1, ...)
    """
    if team_size < 1:
        raise ValueError(f"team_size must be >= 1, got {team_size}")
    if n_students < 0:
        raise ValueError(f"n_students must be >= 0, got {n_students}")

    if n_students == 0:
        return TeamShape(0, 0, 0, team_size, 0)

    # Rule 1: fewer students than a full team → one team
    if n_students <= team_size:
        return TeamShape(
            n_full_teams=0,
            small_size=n_students,
            absorb_count=0,
            team_size=team_size,
            n_students=n_students,
        )

    r = n_students % team_size
    n_full = n_students // team_size

    # Rule 2: clean split
    if r == 0:
        return TeamShape(n_full, 0, 0, team_size, n_students)

    # Rule 3: r is large enough to form its own team
    # Condition: r >= team_size/2 AND r >= 2
    # (r >= 2 prevents a team of 1 when team_size == 2 and r == 1)
    if r >= team_size / 2 and r >= 2:
        return TeamShape(n_full, r, 0, team_size, n_students)

    # Rule 4: absorb remainder into existing teams
    # Special case: if r == 1 and there's only 1 full team, we'd get a team
    # of team_size+1, which is fine. But if team_size == 1 we'd have a team
    # of 2, also fine. The "never team of 1" rule is satisfied as long as
    # absorb_count < n_full (guaranteed since r < team_size and n_full >= 1).
    return TeamShape(n_full, 0, r, team_size, n_students)
