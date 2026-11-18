"""guest access: sample-security and account-management permissions

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-11-19 00:00:00.000000

- security:read:sample lets the guest open the security pages, which then
  serve synthetic data. The guest no longer holds security:read, so any
  endpoint guarded by a real security permission denies it by default.
- account:manage covers self-service account changes (2FA, sessions). Admin
  and analyst get it; the shared guest account does not.
- Creates the guest user so the reserved email exists from the first deploy
  and cannot be claimed through signup.
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

GRANTS = {
    "security:read:sample": ["guest"],
    "account:manage":       ["admin", "analyst"],
}


def upgrade() -> None:
    for perm, roles in GRANTS.items():
        op.execute(f"""
            INSERT INTO permissions (id, name) VALUES (gen_random_uuid(), '{perm}')
            ON CONFLICT (name) DO NOTHING;
        """)
        role_list = ", ".join(f"'{r}'" for r in roles)
        op.execute(f"""
            INSERT INTO role_permissions (id, role_id, permission_id)
            SELECT gen_random_uuid(), r.id, p.id
            FROM roles r JOIN permissions p ON p.name = '{perm}'
            WHERE r.name IN ({role_list})
            ON CONFLICT (role_id, permission_id) DO NOTHING;
        """)

    op.execute("""
        DELETE FROM role_permissions rp
        USING roles r, permissions p
        WHERE rp.role_id = r.id AND rp.permission_id = p.id
          AND r.name = 'guest' AND p.name = 'security:read';
    """)

    op.execute("""
        INSERT INTO users (id, email, password_hash, role, is_active)
        VALUES (gen_random_uuid(), 'guest@demo.invalid', '!', 'guest', true)
        ON CONFLICT (email) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("DELETE FROM users WHERE email = 'guest@demo.invalid' AND role = 'guest';")
    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id)
        SELECT gen_random_uuid(), r.id, p.id
        FROM roles r JOIN permissions p ON p.name = 'security:read'
        WHERE r.name = 'guest'
        ON CONFLICT (role_id, permission_id) DO NOTHING;
    """)
    op.execute("DELETE FROM permissions WHERE name IN ('security:read:sample', 'account:manage');")
