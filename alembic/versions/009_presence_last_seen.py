"""Add last_seen_at to presence_sessions for lobby polling presence.

Revision ID: 009
Revises: 008
Create Date: 2026-05-29

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "presence_sessions",
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("UPDATE presence_sessions SET last_seen_at = connected_at")
    op.create_index(
        "ix_presence_sessions_last_seen_at",
        "presence_sessions",
        ["last_seen_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_presence_sessions_last_seen_at", table_name="presence_sessions")
    op.drop_column("presence_sessions", "last_seen_at")
