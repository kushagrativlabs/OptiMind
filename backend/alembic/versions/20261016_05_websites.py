"""Add websites and website-specific conversations.

Revision ID: 20261016_05
Revises: 20261016_04
Create Date: 2026-10-16
"""

import sqlalchemy as sa

from alembic import op

revision = "20261016_05"
down_revision = "20261016_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "websites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("url", sa.String(length=2_000), nullable=False),
        sa.Column("wordpress_api_url", sa.String(length=2_000), nullable=True),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )
    op.add_column("conversations", sa.Column("website_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_conversations_website_id",
        "conversations",
        "websites",
        ["website_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_conversations_website_id",
        "conversations",
        ["website_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_conversations_website_id", table_name="conversations")
    op.drop_constraint(
        "fk_conversations_website_id", "conversations", type_="foreignkey"
    )
    op.drop_column("conversations", "website_id")
    op.drop_table("websites")
