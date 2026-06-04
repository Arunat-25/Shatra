"""finished_games anonymous flags + indexes

Revision ID: 006
Revises: 005
Create Date: 2026-05-29

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "finished_games",
        sa.Column("white_is_anonymous", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "finished_games",
        sa.Column("black_is_anonymous", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_finished_games_finished_at", "finished_games", ["finished_at"])
    op.create_index(
        "ix_finished_games_room_type_finished_at",
        "finished_games",
        ["room_type", "finished_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_finished_games_room_type_finished_at", table_name="finished_games")
    op.drop_index("ix_finished_games_finished_at", table_name="finished_games")
    op.drop_column("finished_games", "black_is_anonymous")
    op.drop_column("finished_games", "white_is_anonymous")
