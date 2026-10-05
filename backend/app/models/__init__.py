# Import all models so SQLAlchemy's mapper and Alembic autogenerate
# can see every table in Base.metadata.
from app.models.user import User  # noqa: F401
from app.models.cohort import Cohort, CohortMember  # noqa: F401
from app.models.activity import Activity, ActivityLock  # noqa: F401
from app.models.registration import Registration  # noqa: F401
from app.models.team import Team, TeamMember, FormationLog  # noqa: F401

__all__ = [
    "User",
    "Cohort",
    "CohortMember",
    "Activity",
    "ActivityLock",
    "Registration",
    "Team",
    "TeamMember",
    "FormationLog",
]
