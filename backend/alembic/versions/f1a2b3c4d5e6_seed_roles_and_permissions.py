"""seed roles and permissions

Revision ID: f1a2b3c4d5e6
Revises: d4e5f6a7b8c9
Create Date: 2026-11-18 00:00:00.000000

Data migration: makes the admin, analyst, and guest roles and their grants
match ROLE_PERMISSIONS exactly. Every statement is an upsert or a scoped
delete, so running it against a database that already has some or all of
these rows is safe.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ALL_PERMISSIONS = [
    "jobs:read", "jobs:read:live", "alerts:read", "alerts:trigger",
    "anomalies:read", "users:read", "users:manage", "audit:read",
    "security:read", "mode:toggle",
]

ROLES = {
    "admin":   "Full platform access",
    "analyst": "Read-only access to monitoring data",
    "guest":   "Shared read-only demo account",
}

ROLE_PERMISSIONS = {
    "admin":   ALL_PERMISSIONS,
    "analyst": ["jobs:read", "alerts:read", "anomalies:read"],
    # audit:read is deliberately absent: it returns real audit rows.
    "guest":   ["jobs:read", "alerts:read", "anomalies:read", "security:read"],
}


def upgrade() -> None:
    conn = op.get_bind()

    for name in ALL_PERMISSIONS:
        conn.execute(
            sa.text(
                "INSERT INTO permissions (id, name) VALUES (gen_random_uuid(), :name) "
                "ON CONFLICT (name) DO NOTHING"
            ),
            {"name": name},
        )

    for name, description in ROLES.items():
        conn.execute(
            sa.text(
                "INSERT INTO roles (id, name, description) "
                "VALUES (gen_random_uuid(), :name, :description) "
                "ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description"
            ),
            {"name": name, "description": description},
        )

    for role, perms in ROLE_PERMISSIONS.items():
        conn.execute(
            sa.text(
                "INSERT INTO role_permissions (id, role_id, permission_id) "
                "SELECT gen_random_uuid(), r.id, p.id "
                "FROM roles r JOIN permissions p ON p.name = ANY(:perms) "
                "WHERE r.name = :role "
                "ON CONFLICT (role_id, permission_id) DO NOTHING"
            ),
            {"role": role, "perms": perms},
        )
        # Remove grants that are no longer in the canonical set.
        conn.execute(
            sa.text(
                "DELETE FROM role_permissions rp "
                "USING roles r, permissions p "
                "WHERE rp.role_id = r.id AND rp.permission_id = p.id "
                "AND r.name = :role AND NOT (p.name = ANY(:perms))"
            ),
            {"role": role, "perms": perms},
        )


def downgrade() -> None:
    # admin and analyst predate this migration; only the guest role is new.
    op.execute("DELETE FROM roles WHERE name = 'guest';")
