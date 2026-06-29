"""enable rls on rbac and backup_codes tables

Revision ID: d4e5f6a7b8c9
Revises: b7c8d9e0f1a2
Create Date: 2026-06-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ("roles", "permissions", "role_permissions", "backup_codes"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"""
            CREATE POLICY "service_role_all" ON {table}
            FOR ALL TO service_role
            USING (true) WITH CHECK (true);
        """)


def downgrade() -> None:
    for table in ("roles", "permissions", "role_permissions", "backup_codes"):
        op.execute(f'DROP POLICY IF EXISTS "service_role_all" ON {table};')
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
