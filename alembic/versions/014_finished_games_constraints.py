"""finished_games unique session + user history indexes

Revision ID: 014
Revises: 013
Create Date: 2026-06-11

"""

from typing import Sequence, Union

from alembic import op

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_finished_games_room_started",
        "finished_games",
        ["room_id", "started_at"],
    )
    op.create_index(
        "ix_finished_games_white_user_finished_at",
        "finished_games",
        ["white_user_id", "finished_at"],
        postgresql_ops={"finished_at": "DESC"},
    )
    op.create_index(
        "ix_finished_games_black_user_finished_at",
        "finished_games",
        ["black_user_id", "finished_at"],
        postgresql_ops={"finished_at": "DESC"},
    )


def downgrade() -> None:
    op.drop_index("ix_finished_games_black_user_finished_at", table_name="finished_games")
    op.drop_index("ix_finished_games_white_user_finished_at", table_name="finished_games")
    op.drop_constraint("uq_finished_games_room_started", "finished_games", type_="unique")
