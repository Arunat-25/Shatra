"""Drop denormalized username columns from finished_games.

Revision ID: 007
Revises: 006
Create Date: 2026-05-29

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("finished_games", "white_username")
    op.drop_column("finished_games", "black_username")


def downgrade() -> None:
    op.add_column(
        "finished_games",
        sa.Column("white_username", sa.String(32), nullable=True),
    )
    op.add_column(
        "finished_games",
        sa.Column("black_username", sa.String(32), nullable=True),
    )
