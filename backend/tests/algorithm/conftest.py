"""Shared fixtures for algorithm tests."""
import pytest
from app.algorithm.engine import Lock


@pytest.fixture
def students_12():
    return [f"s{i:02d}" for i in range(12)]


@pytest.fixture
def students_20():
    return [f"s{i:02d}" for i in range(20)]


@pytest.fixture
def empty_history():
    return {}


@pytest.fixture
def light_history():
    """A few pairs have met once, recently."""
    return {
        ("s00", "s01"): (1, 2),
        ("s02", "s03"): (1, 5),
        ("s04", "s05"): (1, 10),
    }


@pytest.fixture
def dense_history():
    """Most pairs in a 12-student cohort have met at least once."""
    from itertools import combinations
    students = [f"s{i:02d}" for i in range(12)]
    history = {}
    for i, (a, b) in enumerate(combinations(students, 2)):
        if i % 2 == 0:
            history[(a, b)] = (1, i + 1)
    return history


@pytest.fixture
def together_lock():
    return Lock("s00", "s01", "together")


@pytest.fixture
def apart_lock():
    return Lock("s00", "s01", "apart")
