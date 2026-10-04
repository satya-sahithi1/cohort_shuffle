"""
cohort_shuffle algorithm package.

Public API — everything the formation service needs:

    from backend.algorithm.engine import form_teams, Lock, FormationResult, validate_locks
    from backend.algorithm.scorer import PairHistory, saturation
"""

from .engine import form_teams, Lock, FormationResult, validate_locks
from .scorer import PairHistory, saturation

__all__ = [
    "form_teams",
    "Lock",
    "FormationResult",
    "validate_locks",
    "PairHistory",
    "saturation",
]
