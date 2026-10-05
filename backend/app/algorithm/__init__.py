"""
algorithm — Pure Python team formation module.

No database access. No web framework. Takes student IDs and history,
returns FormationResult.

Public API:
    from app.algorithm.engine import form_teams, FormationResult, Lock
"""

from app.algorithm.engine import form_teams, FormationResult, Lock

__all__ = ["form_teams", "FormationResult", "Lock"]
