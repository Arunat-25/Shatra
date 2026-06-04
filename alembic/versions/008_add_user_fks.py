"""Add FK constraints from finished_games and presence_sessions to users.

Revision ID: 008
Revises: 007
Create Date: 2026-05-29

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE finished_games SET white_user_id = NULL
        WHERE white_user_id IS NOT NULL
          AND white_user_id NOT IN (SELECT id FROM users)
        """
    )
    op.execute(
        """
        UPDATE finished_games SET black_user_id = NULL
        WHERE black_user_id IS NOT NULL
          AND black_user_id NOT IN (SELECT id FROM users)
        """
    )
    op.execute(
        """
        UPDATE presence_sessions SET user_id = NULL
        WHERE user_id IS NOT NULL
          AND user_id NOT IN (SELECT id FROM users)
        """
    )
    op.create_foreign_key(
        "fk_finished_games_white_user",
        "finished_games",
        "users",
        ["white_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_finished_games_black_user",
        "finished_games",
        "users",
        ["black_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_presence_sessions_user",
        "presence_sessions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_presence_sessions_user", "presence_sessions", type_="foreignkey")
    op.drop_constraint("fk_finished_games_black_user", "finished_games", type_="foreignkey")
    op.drop_constraint("fk_finished_games_white_user", "finished_games", type_="foreignkey")
