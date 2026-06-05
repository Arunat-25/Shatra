"""bug_reports table

Revision ID: 010
Revises: 009
Create Date: 2026-06-05

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bug_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("screenshot", sa.LargeBinary(), nullable=True),
        sa.Column("screenshot_mime", sa.String(64), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("client_id", sa.String(64), nullable=True),
        sa.Column("page_url", sa.String(512), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_bug_reports_user_id", "bug_reports", ["user_id"])
    op.create_index("ix_bug_reports_client_id", "bug_reports", ["client_id"])
    op.create_index("ix_bug_reports_created_at", "bug_reports", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_bug_reports_created_at", table_name="bug_reports")
    op.drop_index("ix_bug_reports_client_id", table_name="bug_reports")
    op.drop_index("ix_bug_reports_user_id", table_name="bug_reports")
    op.drop_table("bug_reports")
