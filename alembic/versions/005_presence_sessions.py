"""presence_sessions table

Revision ID: 005
Revises: 004
Create Date: 2026-05-29

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "presence_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", sa.String(64), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_anonymous", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("room_id", sa.String(8), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("disconnected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_presence_sessions_client_id", "presence_sessions", ["client_id"])
    op.create_index("ix_presence_sessions_user_id", "presence_sessions", ["user_id"])
    op.create_index("ix_presence_sessions_connected_at", "presence_sessions", ["connected_at"])


def downgrade() -> None:
    op.drop_index("ix_presence_sessions_connected_at", table_name="presence_sessions")
    op.drop_index("ix_presence_sessions_user_id", table_name="presence_sessions")
    op.drop_index("ix_presence_sessions_client_id", table_name="presence_sessions")
    op.drop_table("presence_sessions")
