import uuid as uuid_lib

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from audit import log_action
from database import get_db
from models import User
from permissions import require_permission

router = APIRouter()


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
