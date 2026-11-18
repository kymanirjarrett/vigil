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
    # These two tables predate Alembic (they were made by create_all), so no
    # earlier migration creates them. Create them here when missing so the
    # chain can build a database from empty; existing databases are untouched.
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("anomaly_events"):
        op.create_table(
            "anomaly_events",
            sa.Column("id",          sa.Integer(), primary_key=True),
            sa.Column("job_name",    sa.String(),  nullable=False),
            sa.Column("run_id",      sa.String(),  nullable=False),
            sa.Column("type",        sa.String(),  nullable=False),
            sa.Column("severity",    sa.String(),  nullable=False),
            sa.Column("message",     sa.String(),  nullable=False),
            sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.UniqueConstraint("run_id", "type", name="uq_anomaly_run_type"),
        )
        op.create_index("ix_anomaly_events_id", "anomaly_events", ["id"])
        op.create_index("ix_anomaly_events_job_name", "anomaly_events", ["job_name"])
    if not inspector.has_table("alert_log"):
        op.create_table(
            "alert_log",
            sa.Column("id",              sa.Integer(), primary_key=True),
            sa.Column("recipient",       sa.String(),  nullable=False),
            sa.Column("job_name",        sa.String(),  nullable=False),
            sa.Column("anomaly_count",   sa.Integer(), nullable=False),
            sa.Column("sent_at",         sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("sendgrid_status", sa.Integer(), nullable=True),
        )
        op.create_index("ix_alert_log_id", "alert_log", ["id"])

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
