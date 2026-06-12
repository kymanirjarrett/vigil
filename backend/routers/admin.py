import uuid as uuid_lib
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from audit import log_action
from database import get_db
from models import Permission, RefreshToken, Role, RolePermission, User
from permissions import invalidate_cache, require_permission

router = APIRouter()

VALID_ROLES = {"admin", "analyst"}


class UserUpdateRequest(BaseModel):
    role:      Optional[str]  = None
    is_active: Optional[bool] = None


@router.post("/users/{user_id}/unlock")
def unlock_user(
    user_id: str,
    request: Request,
    current_user: User = Depends(require_permission("users:manage")),
    db: Session = Depends(get_db),
):
    try:
        uid = uuid_lib.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    target = db.query(User).filter(User.id == uid).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if not target.locked_until:
        return {"message": "Account is not locked", "user_id": user_id}

    target.locked_until = None
    db.commit()

    log_action(
        db, "user.unlocked", request,
        user=current_user,
        resource_type="user",
        resource_id=user_id,
        metadata={"unlocked_by": str(current_user.id)},
    )

    return {"message": "Account unlocked", "user_id": user_id}


@router.delete("/users/{user_id}/sessions")
def revoke_user_sessions(
    user_id: str,
    request: Request,
    current_user: User = Depends(require_permission("users:manage")),
    db: Session = Depends(get_db),
):
    try:
        uid = uuid_lib.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    target = db.query(User).filter(User.id == uid).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.now(timezone.utc)
    db.query(RefreshToken).filter(
        RefreshToken.user_id    == uid,
        ~RefreshToken.is_revoked,
    ).update({"is_revoked": True, "revoked_at": now})
    db.commit()

    log_action(
        db, "user.sessions_revoked", request,
        user=current_user,
        resource_type="user",
        resource_id=user_id,
        metadata={"revoked_by": str(current_user.id)},
    )
    return {"message": "All sessions revoked", "user_id": user_id}


@router.patch("/users/{user_id}")
def update_user(
    user_id: str,
    body: UserUpdateRequest,
    request: Request,
    current_user: User = Depends(require_permission("users:manage")),
    db: Session = Depends(get_db),
):
    try:
        uid = uuid_lib.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    if uid == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot modify your own account")

    target = db.query(User).filter(User.id == uid).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if body.role is not None:
        if body.role not in VALID_ROLES:
            raise HTTPException(status_code=400, detail=f"Role must be one of {VALID_ROLES}")
        old_role       = target.role
        target.role    = body.role
        db.commit()
        log_action(
            db, "user.role_changed", request,
            user=current_user,
            resource_type="user",
            resource_id=user_id,
            metadata={"from": old_role, "to": body.role},
        )

    if body.is_active is not None:
        target.is_active = body.is_active
        db.commit()
        action = "user.reactivated" if body.is_active else "user.deactivated"
        log_action(db, action, request, user=current_user, resource_type="user", resource_id=user_id)

    return {
        "id":        str(target.id),
        "email":     target.email,
        "role":      target.role,
        "is_active": target.is_active,
    }


@router.get("/users")
def list_users(
    _: User = Depends(require_permission("users:manage")),
    db: Session = Depends(get_db),
):
    users = db.query(User).order_by(User.created_at).all()
    return {
        "users": [
            {
                "id":           str(u.id),
                "email":        u.email,
                "role":         u.role,
                "is_active":    u.is_active,
                "demo_mode":    u.demo_mode,
                "locked_until": u.locked_until.isoformat() if u.locked_until else None,
                "created_at":   u.created_at.isoformat() if u.created_at else None,
                "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            }
            for u in users
        ]
    }


@router.get("/permissions")
def list_permissions(
    _: User = Depends(require_permission("users:manage")),
    db: Session = Depends(get_db),
):
    roles    = db.query(Role).order_by(Role.name).all()
    all_perm = db.query(Permission).order_by(Permission.name).all()

    roles_out = []
    for role in roles:
        granted_ids = {
            rp.permission_id
            for rp in db.query(RolePermission).filter(RolePermission.role_id == role.id).all()
        }
        roles_out.append({
            "name":        role.name,
            "description": role.description,
            "permissions": [
                {"id": str(p.id), "name": p.name, "granted": p.id in granted_ids}
                for p in all_perm
            ],
        })

    return {
        "roles":       roles_out,
        "permissions": [p.name for p in all_perm],
    }


@router.post("/roles/{role_name}/permissions/{permission_name}", status_code=201)
def grant_permission(
    role_name: str,
    permission_name: str,
    request: Request,
    current_user: User = Depends(require_permission("users:manage")),
    db: Session = Depends(get_db),
):
    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    perm = db.query(Permission).filter(Permission.name == permission_name).first()
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")

    existing = db.query(RolePermission).filter(
        RolePermission.role_id       == role.id,
        RolePermission.permission_id == perm.id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Permission already granted")

    db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    db.commit()
    invalidate_cache()

    log_action(
        db, "permission.granted", request,
        user=current_user,
        resource_type="role",
        resource_id=role_name,
        metadata={"permission": permission_name},
    )
    return {"message": "Permission granted"}


@router.delete("/roles/{role_name}/permissions/{permission_name}")
def revoke_permission(
    role_name: str,
    permission_name: str,
    request: Request,
    current_user: User = Depends(require_permission("users:manage")),
    db: Session = Depends(get_db),
):
    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    perm = db.query(Permission).filter(Permission.name == permission_name).first()
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")

    deleted = db.query(RolePermission).filter(
        RolePermission.role_id       == role.id,
        RolePermission.permission_id == perm.id,
    ).delete()
    db.commit()

    if not deleted:
        raise HTTPException(status_code=404, detail="Permission not assigned to this role")

    invalidate_cache()

    log_action(
        db, "permission.revoked", request,
        user=current_user,
        resource_type="role",
        resource_id=role_name,
        metadata={"permission": permission_name},
    )
    return {"message": "Permission revoked"}
