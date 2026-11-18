"""remove demo mode; record simulated alerts

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-11-18 12:00:00.000000

Sample data is now the app's default data source (DATA_SOURCE=seed), so the
per-user demo toggle is gone: drop users.demo_mode and the mode:toggle
permission. alert_log.simulated marks alerts recorded without sending email.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("users", "demo_mode")
    # role_permissions rows go with it (ON DELETE CASCADE).
    op.execute("DELETE FROM permissions WHERE name = 'mode:toggle';")
    op.add_column(
        "alert_log",
        sa.Column("simulated", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("alert_log", "simulated")
    op.execute("""
        INSERT INTO permissions (id, name) VALUES (gen_random_uuid(), 'mode:toggle')
        ON CONFLICT (name) DO NOTHING;
    """)
    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id)
        SELECT gen_random_uuid(), r.id, p.id
        FROM roles r JOIN permissions p ON p.name = 'mode:toggle'
        WHERE r.name = 'admin'
        ON CONFLICT (role_id, permission_id) DO NOTHING;
    """)
    op.add_column(
        "users",
        sa.Column("demo_mode", sa.Boolean(), nullable=False, server_default="false"),
    )
