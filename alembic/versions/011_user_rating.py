"""user rating and finished_games rating deltas

Revision ID: 011
Revises: 010
Create Date: 2026-06-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("rating", sa.Integer(), nullable=False, server_default="1500"),
    )
    op.add_column(
        "users",
        sa.Column("rated_games_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "finished_games",
        sa.Column("is_rated", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "finished_games",
        sa.Column("white_rating_delta", sa.Integer(), nullable=True),
    )
    op.add_column(
        "finished_games",
        sa.Column("black_rating_delta", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("finished_games", "black_rating_delta")
    op.drop_column("finished_games", "white_rating_delta")
    op.drop_column("finished_games", "is_rated")
    op.drop_column("users", "rated_games_count")
    op.drop_column("users", "rating")
