"""job details: benefits, team, hiring process and practical terms

Revision ID: b3e1f0a2c7d9
Revises: 90d738b8d474
Create Date: 2026-10-14 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b3e1f0a2c7d9"
down_revision: str | None = "90d738b8d474"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("benefits", postgresql.JSONB(), nullable=False, server_default="[]"))
    op.add_column("jobs", sa.Column("about_team", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("hiring_process", postgresql.JSONB(), nullable=False, server_default="[]"))
    op.add_column("jobs", sa.Column("department", sa.String(length=120), nullable=True))
    op.add_column("jobs", sa.Column("hours_per_week", sa.Integer(), nullable=True))
    op.add_column("jobs", sa.Column("contract_duration_months", sa.Integer(), nullable=True))
    op.add_column("jobs", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("jobs", sa.Column("openings", sa.Integer(), nullable=False, server_default="1"))


def downgrade() -> None:
    for column in ("openings", "start_date", "contract_duration_months", "hours_per_week", "department", "hiring_process", "about_team", "benefits"):
        op.drop_column("jobs", column)
