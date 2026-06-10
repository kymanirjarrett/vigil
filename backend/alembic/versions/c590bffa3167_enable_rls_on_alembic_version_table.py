"""enable rls on alembic_version table

Revision ID: c590bffa3167
Revises: be9e2db0da8c
Create Date: 2026-06-09 21:16:54.577221

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c590bffa3167'
down_revision: Union[str, None] = 'be9e2db0da8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE alembic_version ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY "service_role_all" ON alembic_version
        FOR ALL TO service_role
        USING (true)
        WITH CHECK (true);
    """)


def downgrade() -> None:
    op.execute('DROP POLICY IF EXISTS "service_role_all" ON alembic_version;')
    op.execute("ALTER TABLE alembic_version DISABLE ROW LEVEL SECURITY;")
