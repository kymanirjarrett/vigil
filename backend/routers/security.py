from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from auth_detection import detect_auth_anomalies
from database import get_db
from demo_data import get_demo_security_posture
from models import AuditLogEntry, AuthEvent, User
from permissions import require_permission

router = APIRouter()


def _use_demo(user: User) -> bool:
    return user.role == "analyst" or user.demo_mode


@router.get("/posture")
def get_security_posture(
    current_user: User = Depends(require_permission("security:read")),
    db: Session = Depends(get_db),
):
    if _use_demo(current_user):
        return get_demo_security_posture()

    now       = datetime.now(timezone.utc)
    since_24h = now - timedelta(hours=24)
    since_7d  = now - timedelta(days=7)

    # ── Login activity by hour (last 24h) ──────────────────────────────────
    events_24h = db.query(AuthEvent).filter(AuthEvent.created_at >= since_24h).all()

    hourly: dict = defaultdict(lambda: {"failures": 0, "successes": 0})
    for e in events_24h:
        if not e.created_at:
            continue
        key = e.created_at.replace(minute=0, second=0, microsecond=0).strftime("%H:%M")
        if e.event_type == "login_failure":
            hourly[key]["failures"] += 1
        elif e.event_type == "login_success":
            hourly[key]["successes"] += 1

    login_activity = []
    for i in range(24):
        h   = (now - timedelta(hours=23 - i)).replace(minute=0, second=0, microsecond=0)
        key = h.strftime("%H:%M")
        login_activity.append({
            "hour":      key,
            "failures":  hourly[key]["failures"],
            "successes": hourly[key]["successes"],
        })

    # ── Top 5 source IPs by failures (24h) ─────────────────────────────────
    top_ip_rows = (
        db.query(AuthEvent.ip_address, func.count(AuthEvent.id).label("cnt"))
        .filter(
            AuthEvent.event_type == "login_failure",
            AuthEvent.ip_address.isnot(None),
            AuthEvent.created_at >= since_24h,
        )
        .group_by(AuthEvent.ip_address)
        .order_by(desc("cnt"))
        .limit(5)
        .all()
    )
    top_ips = [{"ip": r.ip_address, "failure_count": r.cnt} for r in top_ip_rows]

    # ── Auth anomaly summary (reuse detection engine on 24h data) ───────────
    event_dicts = [
        {"email": e.email, "event_type": e.event_type,
         "ip_address": e.ip_address, "created_at": e.created_at}
        for e in events_24h
    ]
    anomalies = detect_auth_anomalies(event_dicts)
    anomaly_summary = {
        "total":    len(anomalies),
        "critical": sum(1 for a in anomalies if a["severity"] == "critical"),
        "warning":  sum(1 for a in anomalies if a["severity"] == "warning"),
    }

    # ── Users by role ───────────────────────────────────────────────────────
    role_rows = (
        db.query(User.role, func.count(User.id))
        .filter(User.is_active)
        .group_by(User.role)
        .all()
    )
    users_by_role = [{"role": r, "count": c} for r, c in role_rows]

    # ── Locked accounts ─────────────────────────────────────────────────────
    locked_count = (
        db.query(func.count(User.id))
        .filter(User.locked_until > now)
        .scalar()
    ) or 0

    # ── Recent security-relevant audit events (7d) ──────────────────────────
    recent_rows = (
        db.query(AuditLogEntry)
        .filter(AuditLogEntry.created_at >= since_7d)
        .order_by(desc(AuditLogEntry.created_at))
        .limit(10)
        .all()
    )
    security_events = [
        {
            "action":      r.action,
            "resource_id": r.resource_id,
            "ip_address":  r.ip_address,
            "created_at":  r.created_at.isoformat() if r.created_at else None,
        }
        for r in recent_rows
    ]

    # ── Total failures summary ──────────────────────────────────────────────
    failures_24h = sum(h["failures"] for h in login_activity)

    return {
        "login_activity":  login_activity,
        "top_ips":         top_ips,
        "anomaly_summary": anomaly_summary,
        "users_by_role":   users_by_role,
        "locked_count":    locked_count,
        "failures_24h":    failures_24h,
        "security_events": security_events,
        "source":          "live",
    }
