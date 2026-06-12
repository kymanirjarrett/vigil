"""add refresh_tokens table

Revision ID: ef688e60271f
Revises: 6938d154fa3d
Create Date: 2026-06-11 21:17:44.104242

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ef688e60271f'
down_revision: Union[str, None] = '6938d154fa3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "refresh_tokens",
        sa.Column("id",         sa.UUID(),                  nullable=False),
        sa.Column("user_id",    sa.UUID(),                  nullable=False),
        sa.Column("token_hash", sa.String(),                nullable=False),
        sa.Column("family_id",  sa.UUID(),                  nullable=False),
        sa.Column("is_revoked", sa.Boolean(),               nullable=False, server_default="false"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip_address", sa.String(),                nullable=True),
        sa.Column("user_agent", sa.String(),                nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_refresh_tokens_user_id",    "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)
    op.create_index("ix_refresh_tokens_family_id",  "refresh_tokens", ["family_id"])
    op.create_index("ix_refresh_tokens_is_revoked", "refresh_tokens", ["is_revoked"])
    op.execute("ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY "service_role_all" ON refresh_tokens
        FOR ALL TO service_role
        USING (true) WITH CHECK (true);
    """)


def downgrade() -> None:
    op.execute('DROP POLICY IF EXISTS "service_role_all" ON refresh_tokens;')
    op.execute("ALTER TABLE refresh_tokens DISABLE ROW LEVEL SECURITY;")
    op.drop_index("ix_refresh_tokens_is_revoked", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_family_id",  table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_token_hash", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_id",    table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
