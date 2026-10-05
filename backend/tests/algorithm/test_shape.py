"""Tests for shape.py — team shape calculation."""
import pytest
from app.algorithm.shape import compute_shape


def test_zero_students():
    s = compute_shape(0, 4)
    assert s.total_teams == 0
    assert s.sizes == []


def test_fewer_than_team_size():
    # Rule 1: one team of n
    s = compute_shape(3, 5)
    assert s.total_teams == 1
    assert s.sizes == [3]


def test_exactly_one_team():
    s = compute_shape(4, 4)
    assert s.total_teams == 1
    assert s.sizes == [4]


def test_clean_split():
    # Rule 2: r == 0
    s = compute_shape(12, 4)
    assert s.n_full_teams == 3
    assert s.small_size == 0
    assert s.absorb_count == 0
    assert s.sizes == [4, 4, 4]


def test_remainder_forms_small_team():
    # Rule 3: r=2, team_size=4, r >= 4/2=2 → small team of 2
    s = compute_shape(14, 4)
    assert s.n_full_teams == 3
    assert s.small_size == 2
    assert s.absorb_count == 0
    assert sorted(s.sizes) == [2, 4, 4, 4]


def test_remainder_absorbed():
    # Rule 4: r=1, team_size=4, r < 4/2=2 → absorb into 1 team
    s = compute_shape(13, 4)
    assert s.n_full_teams == 3
    assert s.small_size == 0
    assert s.absorb_count == 1
    assert sorted(s.sizes) == [4, 4, 5]


def test_remainder_3_of_4_forms_small_team():
    # r=3, team_size=4, 3 >= 2 → small team
    s = compute_shape(15, 4)
    assert s.small_size == 3
    assert s.n_full_teams == 3


def test_never_team_of_one_via_absorption():
    # r=1 with team_size=2: one team of 3 instead of two teams of 2 + one of 1
    s = compute_shape(5, 2)
    assert 1 not in s.sizes


def test_team_size_2_even():
    s = compute_shape(6, 2)
    assert s.sizes == [2, 2, 2]


def test_team_size_2_odd():
    # r=1, r < 2/2=1 is False (1 < 1 is False), r >= 2 is False
    # So absorb — one team of 3
    s = compute_shape(7, 2)
    assert sorted(s.sizes) == [2, 2, 3]


def test_large_cohort():
    s = compute_shape(62, 6)
    total = sum(s.sizes)
    assert total == 62
    assert all(t >= 2 for t in s.sizes)


def test_total_students_preserved():
    for n in range(1, 50):
        for k in range(2, 8):
            s = compute_shape(n, k)
            assert sum(s.sizes) == n, f"n={n} k={k} sizes={s.sizes}"


def test_no_team_of_one():
    for n in range(2, 50):
        for k in range(2, 8):
            s = compute_shape(n, k)
            assert all(t != 1 for t in s.sizes), f"n={n} k={k} got team of 1: {s.sizes}"


def test_invalid_team_size():
    with pytest.raises(ValueError):
        compute_shape(10, 0)
