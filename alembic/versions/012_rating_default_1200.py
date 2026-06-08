"""Set default user rating to 1200

Revision ID: 012
Revises: 011
Create Date: 2026-06-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "rating",
        server_default="1200",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )
    op.execute(
        "UPDATE users SET rating = 1200 "
        "WHERE rating = 1500 AND rated_games_count = 0"
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "rating",
        server_default="1500",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )
