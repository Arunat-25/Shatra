"""Rating antifraud: pair win limits and smurf-farm gain block

Revision ID: 013
Revises: 012
Create Date: 2026-06-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("rating_gain_blocked_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "finished_games",
        sa.Column("loser_rated_games_before", sa.Integer(), nullable=True),
    )
    op.add_column(
        "finished_games",
        sa.Column(
            "white_gain_capped",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "finished_games",
        sa.Column(
            "black_gain_capped",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("finished_games", "black_gain_capped")
    op.drop_column("finished_games", "white_gain_capped")
    op.drop_column("finished_games", "loser_rated_games_before")
    op.drop_column("users", "rating_gain_blocked_until")
