"""add totp to users

Revision ID: b7c8d9e0f1a2
Revises: 3c7f91a85b2e
Create Date: 2026-06-11 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, None] = '3c7f91a85b2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("totp_secret",  sa.String(),  nullable=True))
    op.add_column("users", sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default="false"))

    op.create_table(
        "backup_codes",
        sa.Column("id",         sa.UUID(),                  nullable=False),
        sa.Column("user_id",    sa.UUID(),                  nullable=False),
        sa.Column("code_hash",  sa.String(),                nullable=False),
        sa.Column("used",       sa.Boolean(),               nullable=False, server_default="false"),
        sa.Column("used_at",    sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_backup_codes_user_id", "backup_codes", ["user_id"])

    op.execute("ALTER TABLE backup_codes ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY "service_role_all" ON backup_codes
        FOR ALL TO service_role
        USING (true) WITH CHECK (true);
    """)


def downgrade() -> None:
    op.execute('DROP POLICY IF EXISTS "service_role_all" ON backup_codes;')
    op.execute("ALTER TABLE backup_codes DISABLE ROW LEVEL SECURITY;")
    op.drop_index("ix_backup_codes_user_id", table_name="backup_codes")
    op.drop_table("backup_codes")

    op.drop_column("users", "totp_enabled")
    op.drop_column("users", "totp_secret")
