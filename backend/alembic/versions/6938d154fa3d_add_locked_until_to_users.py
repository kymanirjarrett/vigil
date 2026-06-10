"""add locked_until to users

Revision ID: 6938d154fa3d
Revises: c590bffa3167
Create Date: 2026-06-10 19:16:50.879209

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6938d154fa3d'
down_revision: Union[str, None] = 'c590bffa3167'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "locked_until")
