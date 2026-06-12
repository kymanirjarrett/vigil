import time

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Permission, Role, RolePermission, User
from routers.auth import get_current_user

# Static fallback used if DB tables aren't reachable yet
PERMISSIONS = {
    "admin": {
        "jobs:read", "jobs:read:live", "alerts:read", "alerts:trigger",
        "anomalies:read", "users:read", "users:manage", "audit:read",
        "security:read", "mode:toggle",
    },
    "analyst": {
        "jobs:read", "alerts:read", "anomalies:read",
    },
}

_CACHE_TTL = 300  # seconds
_perm_cache: dict = {}
_cache_ts: float = 0.0


def invalidate_cache() -> None:
    global _cache_ts
    _cache_ts = 0.0


def _load_permissions(db: Session) -> dict:
    global _perm_cache, _cache_ts
    now = time.monotonic()
    if _perm_cache and (now - _cache_ts) < _CACHE_TTL:
        return _perm_cache
    try:
        roles = db.query(Role).all()
        result: dict = {}
        for role in roles:
            perms = (
                db.query(Permission.name)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .filter(RolePermission.role_id == role.id)
                .all()
            )
            result[role.name] = {p.name for p in perms}
        if result:
            _perm_cache = result
            _cache_ts = now
        return result or PERMISSIONS
    except Exception:
        return PERMISSIONS


def has_permission(role: str, permission: str, db: Session = None) -> bool:
    perms = _load_permissions(db) if db is not None else PERMISSIONS
    return permission in perms.get(role, set())


def require_permission(permission: str):
    def checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if not has_permission(current_user.role, permission, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return checker
