from fastapi import Depends, HTTPException, status
from routers.auth import get_current_user
from models import User

PERMISSIONS = {
    "admin": {
        "jobs:read",
        "jobs:read:live",
        "alerts:read",
        "alerts:trigger",
        "anomalies:read",
        "users:read",
        "users:manage",
        "audit:read",
        "security:read",
        "mode:toggle",
    },
    "analyst": {
        "jobs:read",
        "alerts:read",
        "anomalies:read",
    },
}


def has_permission(role: str, permission: str) -> bool:
    return permission in PERMISSIONS.get(role, set())


def require_permission(permission: str):
    def checker(current_user: User = Depends(get_current_user)):
        if not has_permission(current_user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return checker
