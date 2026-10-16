"""Add generation metrics to conversation messages.

Revision ID: 20261016_03
Revises: 20261015_02
Create Date: 2026-10-16
"""

import sqlalchemy as sa

from alembic import op

revision = "20261016_03"
down_revision = "20261015_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("metrics", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "metrics")
