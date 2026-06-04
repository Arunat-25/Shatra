"""finished_games table

Revision ID: 003
Revises: 002
Create Date: 2026-05-29

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "finished_games",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("room_id", sa.String(8), nullable=False),
        sa.Column("room_type", sa.String(16), nullable=False),
        sa.Column("white_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("black_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("white_client_id", sa.String(64), nullable=True),
        sa.Column("black_client_id", sa.String(64), nullable=True),
        sa.Column("white_username", sa.String(32), nullable=True),
        sa.Column("black_username", sa.String(32), nullable=True),
        sa.Column("winner_color", sa.String(8), nullable=True),
        sa.Column("reason", sa.String(32), nullable=True),
        sa.Column("time_control", sa.Integer(), nullable=True),
        sa.Column("increment", sa.Integer(), nullable=True),
        sa.Column("timer_white_final", sa.Float(), nullable=True),
        sa.Column("timer_black_final", sa.Float(), nullable=True),
        sa.Column("moves_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("move_history", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("final_board", postgresql.JSONB(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_finished_games_room_id", "finished_games", ["room_id"])


def downgrade() -> None:
    op.drop_index("ix_finished_games_room_id", table_name="finished_games")
    op.drop_table("finished_games")
