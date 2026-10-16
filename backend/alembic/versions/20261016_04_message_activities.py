"""Add agent activities to conversation messages.

Revision ID: 20261016_04
Revises: 20261016_03
Create Date: 2026-10-16
"""

import sqlalchemy as sa

from alembic import op

revision = "20261016_04"
down_revision = "20261016_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column(
            "activities",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("messages", "activities")
