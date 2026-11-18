"""add rbac tables

Revision ID: 3c7f91a85b2e
Revises: ef688e60271f
Create Date: 2026-06-11 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '3c7f91a85b2e'
down_revision: Union[str, None] = 'ef688e60271f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tolerate tables that Base.metadata.create_all() made before this migration
    # ran (production hit this). Alembic owns the schema from here on.
    existing = set(sa.inspect(op.get_bind()).get_table_names())

    if "roles" not in existing:
        op.create_table(
            "roles",
            sa.Column("id",          sa.UUID(),    nullable=False),
            sa.Column("name",        sa.String(),  nullable=False),
            sa.Column("description", sa.String(),  nullable=True),
            sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )
    op.create_index("ix_roles_name", "roles", ["name"], unique=True, if_not_exists=True)

    if "permissions" not in existing:
        op.create_table(
            "permissions",
            sa.Column("id",         sa.UUID(),   nullable=False),
            sa.Column("name",       sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )
    op.create_index("ix_permissions_name", "permissions", ["name"], unique=True, if_not_exists=True)

    if "role_permissions" not in existing:
        op.create_table(
            "role_permissions",
            sa.Column("id",            sa.UUID(), nullable=False),
            sa.Column("role_id",       sa.UUID(), nullable=False),
            sa.Column("permission_id", sa.UUID(), nullable=False),
            sa.Column("created_at",    sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["role_id"],       ["roles.id"],       ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
        )
    op.create_index("ix_role_permissions_role_id",       "role_permissions", ["role_id"], if_not_exists=True)
    op.create_index("ix_role_permissions_permission_id", "role_permissions", ["permission_id"], if_not_exists=True)

    # RLS
    for table in ("roles", "permissions", "role_permissions"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f'DROP POLICY IF EXISTS "service_role_all" ON {table};')
        op.execute(f"""
            CREATE POLICY "service_role_all" ON {table}
            FOR ALL TO service_role
            USING (true) WITH CHECK (true);
        """)

    # Seed roles
    op.execute("""
        INSERT INTO roles (id, name, description) VALUES
        (gen_random_uuid(), 'admin',   'Full platform access'),
        (gen_random_uuid(), 'analyst', 'Read-only access to monitoring data')
        ON CONFLICT (name) DO NOTHING;
    """)

    # Seed permissions
    op.execute("""
        INSERT INTO permissions (id, name) VALUES
        (gen_random_uuid(), 'jobs:read'),
        (gen_random_uuid(), 'jobs:read:live'),
        (gen_random_uuid(), 'alerts:read'),
        (gen_random_uuid(), 'alerts:trigger'),
        (gen_random_uuid(), 'anomalies:read'),
        (gen_random_uuid(), 'users:read'),
        (gen_random_uuid(), 'users:manage'),
        (gen_random_uuid(), 'audit:read'),
        (gen_random_uuid(), 'security:read'),
        (gen_random_uuid(), 'mode:toggle')
        ON CONFLICT (name) DO NOTHING;
    """)

    # Grant all permissions to admin
    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id)
        SELECT gen_random_uuid(), r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'admin'
        ON CONFLICT (role_id, permission_id) DO NOTHING;
    """)

    # Grant subset to analyst
    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id)
        SELECT gen_random_uuid(), r.id, p.id
        FROM roles r
        JOIN permissions p ON p.name IN ('jobs:read', 'alerts:read', 'anomalies:read')
        WHERE r.name = 'analyst'
        ON CONFLICT (role_id, permission_id) DO NOTHING;
    """)


def downgrade() -> None:
    for table in ("role_permissions", "permissions", "roles"):
        op.execute(f'DROP POLICY IF EXISTS "service_role_all" ON {table};')
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")

    op.drop_index("ix_role_permissions_permission_id", table_name="role_permissions")
    op.drop_index("ix_role_permissions_role_id",       table_name="role_permissions")
    op.drop_table("role_permissions")

    op.drop_index("ix_permissions_name", table_name="permissions")
    op.drop_table("permissions")

    op.drop_index("ix_roles_name", table_name="roles")
    op.drop_table("roles")
