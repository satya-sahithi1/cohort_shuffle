"""Change formation_logs.random_seed from Integer to BigInteger.

The algorithm generates seeds via random.randrange(2**32), which can produce
values up to 4_294_967_295. PostgreSQL's INT (32-bit signed) overflows at
2_147_483_647. BIGINT (64-bit signed) covers the full range safely.

Revision ID: 0002
Revises    : 0001
Create Date: 2026-10-06
"""

from alembic import op
import sqlalchemy as sa

# ── Revision identifiers ──────────────────────────────────────────────────────
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "formation_logs",
        "random_seed",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "formation_logs",
        "random_seed",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
    )
