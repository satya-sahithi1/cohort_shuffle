"""
cohort_shuffle algorithm package.
Imports use algorithm.* (FIX B15).
"""
from algorithm.engine import form_teams, Lock, FormationResult, validate_locks
from algorithm.scorer import PairHistory, saturation, has_met

__all__ = ["form_teams", "Lock", "FormationResult", "validate_locks",
           "PairHistory", "saturation", "has_met"]
