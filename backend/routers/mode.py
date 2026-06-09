from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from database import get_db
from models import User
from permissions import require_permission
from audit import log_action

router = APIRouter()


@router.post("/toggle")
def toggle_mode(
    request: Request,
    current_user: User = Depends(require_permission("mode:toggle")),
    db: Session = Depends(get_db),
):
    """Flip the admin's live/demo mode preference."""
    current_user.demo_mode = not current_user.demo_mode
    db.commit()

    new_mode = "demo" if current_user.demo_mode else "live"
    log_action(db, "mode.toggled", request, user=current_user,
               metadata={"new_mode": new_mode})

    return {"demo_mode": current_user.demo_mode, "mode": new_mode}
