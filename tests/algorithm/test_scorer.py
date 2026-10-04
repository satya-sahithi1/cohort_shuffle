"""
test_scorer.py — Tests for scorer.py

Covers:
  - pair_score: never met, met once, met multiple times
  - team_score: sum of pairs
  - marginal_score: cost of adding a student
  - arrangement_score: total across all teams
  - count_new_pairs: tie-breaker metric
  - saturation: fraction of pairs exhausted
  - is_better: two-key ranking
"""

import pytest
from algorithm.scorer import (
    pair_score,
    team_score,
    marginal_score,
    arrangement_score,
    count_new_pairs,
    saturation,
    is_better,
    pair_key,
)


class TestPairScore:
    def test_never_met_is_zero(self, empty_history):
        assert pair_score("A", "B", empty_history) == 0

    def test_met_once_is_positive(self):
        # FIX B1: any met pair must score > 0, even very old
        h = {pair_key("A", "B"): (1, 9999)}
        assert pair_score("A", "B", h) > 0

    def test_met_once_recently(self):
        h = {pair_key("A", "B"): (1, 5)}
        assert pair_score("A", "B", h) > 0

    def test_met_once_long_ago(self):
        h = {pair_key("A", "B"): (1, 100)}
        assert pair_score("A", "B", h) > 0

    def test_met_beats_never_met_regardless_of_age(self):
        # FIX B1: pair met 4000 days ago still scores higher than never-met
        h = {pair_key("A", "B"): (1, 4000)}
        assert pair_score("A", "B", h) > pair_score("A", "C", {})

    def test_met_twice_is_worse(self):
        h_once = {pair_key("A", "B"): (1, 50)}
        h_twice = {pair_key("A", "B"): (2, 50)}
        assert pair_score("A", "B", h_twice) > pair_score("A", "B", h_once)

    def test_recent_is_worse_than_old(self):
        h_recent = {pair_key("A", "B"): (1, 2)}
        h_old = {pair_key("A", "B"): (1, 200)}
        assert pair_score("A", "B", h_recent) > pair_score("A", "B", h_old)

    def test_symmetric(self, small_history):
        assert pair_score("A", "B", small_history) == pair_score("B", "A", small_history)

    def test_key_order_does_not_matter(self):
        h = {pair_key("Z", "A"): (1, 10)}
        assert pair_score("A", "Z", h) == pair_score("Z", "A", h)


class TestHasMet:
    def test_never_met(self, empty_history):
        from algorithm.scorer import has_met
        assert has_met("A", "B", empty_history) is False

    def test_has_met(self):
        from algorithm.scorer import has_met
        h = {pair_key("A", "B"): (1, 10)}
        assert has_met("A", "B", h) is True
        assert has_met("B", "A", h) is True

    def test_old_pair_still_has_met(self):
        # FIX B2: has_met must not depend on pair_score > 0
        from algorithm.scorer import has_met
        h = {pair_key("A", "B"): (1, 9999)}
        assert has_met("A", "B", h) is True


class TestTeamScore:
    def test_team_of_strangers_is_zero(self, empty_history):
        assert team_score(["A", "B", "C"], empty_history) == 0

    def test_team_with_one_pair(self):
        h = {pair_key("A", "B"): (1, 50)}
        # A-C and B-C are strangers, only A-B has history
        score = team_score(["A", "B", "C"], h)
        assert score == pair_score("A", "B", h)

    def test_solo_team_is_zero(self, empty_history):
        assert team_score(["A"], empty_history) == 0


class TestMarginalScore:
    def test_adding_to_empty_team_is_zero(self, empty_history):
        assert marginal_score("A", [], empty_history) == 0

    def test_adding_stranger_to_known_team_is_zero(self, empty_history):
        assert marginal_score("X", ["A", "B", "C"], empty_history) == 0

    def test_adding_repeat_increases_score(self, small_history):
        # A has history with B and C
        cost = marginal_score("A", ["B", "C"], small_history)
        assert cost > 0


class TestArrangementScore:
    def test_all_strangers_is_zero(self, empty_history):
        teams = [["A", "B"], ["C", "D"], ["E", "F"]]
        assert arrangement_score(teams, empty_history) == 0

    def test_sums_across_teams(self):
        h = {
            pair_key("A", "B"): (1, 50),
            pair_key("C", "D"): (1, 50),
        }
        teams = [["A", "B"], ["C", "D"]]
        assert arrangement_score(teams, h) == pair_score("A", "B", h) + pair_score("C", "D", h)


class TestCountNewPairs:
    def test_all_new(self, empty_history):
        teams = [["A", "B", "C"], ["D", "E", "F"]]
        # 3 pairs per team = 6 total
        assert count_new_pairs(teams, empty_history) == 6

    def test_none_new(self, saturated_history, students_10):
        # Put first 4 students in one team — all pairs exist in history
        team = students_10[:4]
        teams = [team, students_10[4:8], students_10[8:]]
        result = count_new_pairs(teams, saturated_history)
        assert result == 0

    def test_partial(self):
        h = {pair_key("A", "B"): (1, 10)}
        teams = [["A", "B", "C"]]
        # A-B already met, A-C and B-C are new → 2 new pairs
        assert count_new_pairs(teams, h) == 2


class TestSaturation:
    def test_no_history(self, empty_history):
        assert saturation(empty_history, 10) == 0.0

    def test_fully_saturated(self, saturated_history, students_10):
        # All 10*(10-1)/2 = 45 pairs are in the history
        result = saturation(saturated_history, 10)
        assert result == pytest.approx(1.0)

    def test_partial_saturation(self):
        # 1 pair out of 45 possible (10 students)
        h = {pair_key("s01", "s02"): (1, 10)}
        result = saturation(h, 10)
        assert result == pytest.approx(1 / 45)

    def test_fewer_than_two_students(self, empty_history):
        assert saturation(empty_history, 1) == 0.0
        assert saturation(empty_history, 0) == 0.0


class TestIsBetter:
    def test_lower_score_wins(self):
        assert is_better(5, 10, 10, 10) is True

    def test_higher_score_loses(self):
        assert is_better(15, 10, 10, 10) is False

    def test_equal_score_more_new_pairs_wins(self):
        assert is_better(10, 8, 10, 5) is True

    def test_equal_score_fewer_new_pairs_loses(self):
        assert is_better(10, 3, 10, 5) is False

    def test_equal_score_equal_new_pairs_is_not_better(self):
        assert is_better(10, 5, 10, 5) is False
