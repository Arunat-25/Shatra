"""remove legacy email columns (if present from older 001)

Revision ID: 002
Revises: 001
Create Date: 2026-05-29

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = {c["name"] for c in insp.get_columns("users")}
    if "email" not in columns:
        return

    indexes = {idx["name"] for idx in insp.get_indexes("users")}
    if "ix_users_email" in indexes:
        op.drop_index("ix_users_email", table_name="users")
    if "email_verified_at" in columns:
        op.drop_column("users", "email_verified_at")
    op.drop_column("users", "email")


def downgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(320), nullable=False, server_default=""))
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.alter_column("users", "email", server_default=None)
