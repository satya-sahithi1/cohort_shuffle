"""
alembic/env.py — Alembic migration environment.

This file is run by Alembic when you execute:
    alembic revision --autogenerate -m "description"   ← detect model changes
    alembic upgrade head                                ← apply all migrations
    alembic downgrade -1                               ← undo last migration

How autogenerate works:
  Alembic compares the current DB schema against the SQLAlchemy models
  (found via Base.metadata) and generates a migration script with the diff.
  You review the script, then run `alembic upgrade head` to apply it.

Important: import ALL models before the run_migrations calls below, so
  Alembic can see every table in Base.metadata.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Alembic Config object — gives access to alembic.ini values
config = context.config

# Set up Python logging from alembic.ini config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Import everything so Alembic can see all tables ───────────────────────────
# All models must be imported here (even if not used directly) so that
# Base.metadata contains every table and autogenerate detects them.
from app.database import Base  # noqa: F401 — Base.metadata used below
import app.models  # noqa: F401 — imports all models via models/__init__.py

target_metadata = Base.metadata

# ── Override DB URL from app config ───────────────────────────────────────────
# This ensures Alembic uses the same DB as the app, not the alembic.ini value.
from app.config import get_settings  # noqa: E402

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)


# ── Offline mode (generate SQL without connecting) ────────────────────────────
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (connect and run) ─────────────────────────────────────────────
def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
