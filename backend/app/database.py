"""
database.py — SQLAlchemy async engine and session factory.

Two things are exported:
  - Base: the declarative base all models inherit from
  - get_db: FastAPI dependency that yields a DB session per request

How it works:
  - create_async_engine creates a connection pool to PostgreSQL.
  - AsyncSession is the unit-of-work: all reads/writes in one request
    go through one session, which is committed or rolled back together.
  - get_db is a FastAPI dependency. Route handlers declare it as a
    parameter and get a fresh session injected automatically.

Usage in a route handler:
    from app.database import get_db
    from sqlalchemy.ext.asyncio import AsyncSession

    @router.get("/example")
    async def example(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(User))
        ...
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# The engine manages the connection pool.
# echo=True logs all SQL in debug mode — useful for development.
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,   # checks connection health before using it
)

# Session factory — call this to get a new session.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # objects stay usable after commit
)


class Base(DeclarativeBase):
    """
    All ORM models inherit from this.
    Alembic uses it to discover tables for migrations.
    """
    pass


async def get_db():
    """
    FastAPI dependency. Yields one AsyncSession per request.
    Automatically closes the session when the request finishes.

    Usage:
        async def my_route(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
