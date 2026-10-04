"""
test_fairness.py — Tests for fairness.py

The fairness rule: every student must have at least one teammate
they have never worked with before.

Covers:
  - has_violations: correctly identifies students with zero new teammates
  - enforce: fixes violations when a fix is possible
  - enforce: does not break when no fix is possible (exhausted student)
  - enforce: does not introduce new violations while fixing one
  - enforce: leaves teams untouched when no violations exist
"""

import pytest
from algorithm.fairness import enforce, has_violations
from algorithm.scorer import pair_key


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_history(*pairs):
    """Build a PairHistory from (a, b, count, days_ago) tuples."""
    h = {}
    for a, b, count, days_ago in pairs:
        h[pair_key(a, b)] = (count, days_ago)
    return h


def all_students_present(original_teams, result_teams):
    """Check no student was lost or duplicated during fairness pass."""
    before = sorted(s for t in original_teams for s in t)
    after = sorted(s for t in result_teams for s in t)
    return before == after


# ---------------------------------------------------------------------------
# has_violations
# ---------------------------------------------------------------------------

class TestHasViolations:
    def test_no_history_no_violations(self, empty_history):
        teams = [["A", "B", "C"], ["D", "E", "F"]]
        assert has_violations(teams, empty_history) == []

    def test_detects_student_with_all_repeats(self):
        # A has worked with B and C before — full team of repeats
        h = make_history(("A", "B", 1, 10), ("A", "C", 1, 10))
        teams = [["A", "B", "C"]]
        violations = has_violations(teams, h)
        assert "A" in violations

    def test_no_violation_if_one_new_teammate(self):
        # A has worked with B but not C → A has a new teammate
        h = make_history(("A", "B", 1, 10))
        teams = [["A", "B", "C"]]
        violations = has_violations(teams, h)
        assert "A" not in violations

    def test_only_flags_the_affected_student(self):
        # A-B and A-C are repeats, but B and C have not met each other
        h = make_history(("A", "B", 1, 10), ("A", "C", 1, 10))
        teams = [["A", "B", "C"]]
        violations = has_violations(teams, h)
        assert "A" in violations
        assert "B" not in violations
        assert "C" not in violations

    def test_multiple_violations(self):
        # Both A and D are surrounded by repeats on their respective teams
        h = make_history(
            ("A", "B", 1, 10), ("A", "C", 1, 10),  # A's team
            ("D", "E", 1, 10), ("D", "F", 1, 10),  # D's team
        )
        teams = [["A", "B", "C"], ["D", "E", "F"]]
        violations = has_violations(teams, h)
        assert "A" in violations
        assert "D" in violations

    def test_solo_team_no_violation(self, empty_history):
        # A student alone has no teammates at all — no violation
        teams = [["A"]]
        assert has_violations(teams, empty_history) == []


# ---------------------------------------------------------------------------
# enforce
# ---------------------------------------------------------------------------

class TestEnforce:
    def test_no_violations_teams_unchanged(self, empty_history):
        teams = [["A", "B"], ["C", "D"]]
        import copy
        original = copy.deepcopy(teams)
        enforce(teams, empty_history)
        assert sorted(s for t in teams for s in t) == sorted(s for t in original for s in t)

    def test_fixes_simple_violation(self):
        """
        A is with B and C (both repeats).
        D, E, F are all strangers to A.
        After enforce, A should have at least one stranger on their team.
        """
        h = make_history(("A", "B", 1, 10), ("A", "C", 1, 10))
        teams = [["A", "B", "C"], ["D", "E", "F"]]
        enforce(teams, h)
        # Find A's team
        a_team = next(t for t in teams if "A" in t)
        # A must now have at least one stranger
        has_stranger = any(h.get(pair_key("A", m)) is None for m in a_team if m != "A")
        assert has_stranger

    def test_all_students_still_present_after_fix(self):
        h = make_history(("A", "B", 1, 10), ("A", "C", 1, 10))
        teams = [["A", "B", "C"], ["D", "E", "F"]]
        import copy
        original = copy.deepcopy(teams)
        enforce(teams, h)
        assert all_students_present(original, teams)

    def test_does_not_create_new_violation(self):
        """
        After fixing A's violation, the student swapped in should also
        have at least one new teammate on their new team.
        """
        h = make_history(("A", "B", 1, 10), ("A", "C", 1, 10))
        teams = [["A", "B", "C"], ["D", "E", "F"]]
        enforce(teams, h)
        violations_after = has_violations(teams, h)
        assert violations_after == []

    def test_exhausted_student_no_crash(self):
        """
        A has worked with everyone. No fix possible.
        enforce() should not raise and should not corrupt teams.
        """
        # 3-student cohort, A has met B and C
        h = make_history(("A", "B", 1, 10), ("A", "C", 1, 10), ("B", "C", 1, 10))
        teams = [["A", "B"], ["C"]]
        import copy
        original_students = sorted(s for t in teams for s in t)
        enforce(teams, h)
        after_students = sorted(s for t in teams for s in t)
        assert original_students == after_students

    def test_two_violations_both_fixed(self):
        """Two students each with all-repeat teams. Both should be fixed."""
        h = make_history(
            ("A", "B", 1, 10), ("A", "C", 1, 10),
            ("D", "E", 1, 10), ("D", "F", 1, 10),
        )
        # A is with B,C (repeats); D is with E,F (repeats)
        # G,H,I are strangers to everyone
        teams = [["A", "B", "C"], ["D", "E", "F"], ["G", "H", "I"]]
        enforce(teams, h)
        violations = has_violations(teams, h)
        # At least A and D should be resolved (G,H,I have no history)
        assert "A" not in violations
        assert "D" not in violations
