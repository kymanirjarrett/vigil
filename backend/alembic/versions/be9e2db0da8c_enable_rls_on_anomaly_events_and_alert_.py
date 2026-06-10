"""enable rls on anomaly_events and alert_log

Revision ID: be9e2db0da8c
Revises: 84f3fb6c93e3
Create Date: 2026-06-09 21:09:52.139778

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'be9e2db0da8c'
down_revision: Union[str, None] = '84f3fb6c93e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE anomaly_events ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY "service_role_all" ON anomaly_events
        FOR ALL TO service_role
        USING (true)
        WITH CHECK (true);
    """)
    op.execute("ALTER TABLE alert_log ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY "service_role_all" ON alert_log
        FOR ALL TO service_role
        USING (true)
        WITH CHECK (true);
    """)


def downgrade() -> None:
    op.execute('DROP POLICY IF EXISTS "service_role_all" ON alert_log;')
    op.execute("ALTER TABLE alert_log DISABLE ROW LEVEL SECURITY;")
    op.execute('DROP POLICY IF EXISTS "service_role_all" ON anomaly_events;')
    op.execute("ALTER TABLE anomaly_events DISABLE ROW LEVEL SECURITY;")
