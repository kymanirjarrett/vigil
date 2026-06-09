"""add auth_events table

Revision ID: 84f3fb6c93e3
Revises: e3267d5e4842
Create Date: 2026-06-08 23:25:47.828478

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '84f3fb6c93e3'
down_revision: Union[str, None] = 'e3267d5e4842'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auth_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auth_events_email", "auth_events", ["email"])
    op.create_index("ix_auth_events_event_type", "auth_events", ["event_type"])
    op.create_index("ix_auth_events_created_at", "auth_events", ["created_at"])
    op.execute("ALTER TABLE auth_events ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY "service_role_all" ON auth_events
        FOR ALL TO service_role
        USING (true)
        WITH CHECK (true);
    """)


def downgrade() -> None:
    op.execute('DROP POLICY IF EXISTS "service_role_all" ON auth_events;')
    op.execute("ALTER TABLE auth_events DISABLE ROW LEVEL SECURITY;")
    op.drop_index("ix_auth_events_created_at", table_name="auth_events")
    op.drop_index("ix_auth_events_event_type", table_name="auth_events")
    op.drop_index("ix_auth_events_email", table_name="auth_events")
    op.drop_table("auth_events")
