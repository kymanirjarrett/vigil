from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User
from permissions import require_permission

router = APIRouter()


@router.post("/toggle")
def toggle_mode(
    current_user: User = Depends(require_permission("mode:toggle")),
    db: Session = Depends(get_db),
):
    """Flip the admin's live/demo mode preference."""
    current_user.demo_mode = not current_user.demo_mode
    db.commit()
    return {
        "demo_mode": current_user.demo_mode,
        "mode": "demo" if current_user.demo_mode else "live",
    }
