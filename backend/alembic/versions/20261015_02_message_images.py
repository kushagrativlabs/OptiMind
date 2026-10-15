"""Add image attachments to conversation messages.

Revision ID: 20261015_02
Revises: 20261014_01
Create Date: 2026-10-15
"""

import sqlalchemy as sa

from alembic import op

revision = "20261015_02"
down_revision = "20261014_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column(
            "images",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("messages", "images")
