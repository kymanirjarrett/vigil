"""enable rls on users table

Revision ID: 6936c20009b1
Revises: bf938d8045ec
Create Date: 2026-06-08 22:39:55.167983

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '6936c20009b1'
down_revision: Union[str, None] = 'bf938d8045ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY "service_role_all" ON users
        FOR ALL
        TO service_role
        USING (true)
        WITH CHECK (true);
    """)


def downgrade() -> None:
    op.execute('DROP POLICY IF EXISTS "service_role_all" ON users;')
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY;")
