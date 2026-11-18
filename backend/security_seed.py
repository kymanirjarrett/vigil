"""Synthetic security data for the shared guest account.

Real auth events and audit rows are never shown to the guest. Everything here
is generated relative to the current time from a fixed seed, uses addresses
from the documentation ranges (RFC 5737) and fictional emails, and every IP
passes through mask_ip() on the way out.

One story runs through all four security pages:
  ~5 min ago   credential stuffing: 14 accounts tried from one IP
  ~15 min ago  brute force: 7 failures against alice@acme-corp.io, account locked
  past 24 h    normal sign-ins from a handful of office and VPN addresses
"""
import random
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from auth_detection import detect_auth_anomalies

_NS = uuid.UUID("6f1c2a52-3c3e-4b8e-9d0a-5b7f6c2e9a10")

STUFFING_IP   = "203.0.113.45"
BRUTE_IP      = "198.51.100.23"
NORMAL_IPS    = ["192.0.2.10", "192.0.2.24", "198.51.100.7", "203.0.113.80"]
BRUTE_TARGET  = "alice@acme-corp.io"
TEAM          = ["admin@acme-corp.io", "alice@acme-corp.io", "bob@acme-corp.io",
                 "carol@acme-corp.io", "dan@acme-corp.io"]
UA_BROWSER    = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 Safari/605.1.15"
UA_SCRIPT     = "python-requests/2.31.0"


def mask_ip(ip: str | None) -> str | None:
    """203.0.113.45 -> 203.0.113.x ; 2001:db8:1::5 -> 2001:db8:1:x"""
    if not ip:
        return ip
    if ":" in ip:
        return ":".join(ip.split(":")[:3]) + ":x"
    parts = ip.split(".")
    return ".".join(parts[:3] + ["x"]) if len(parts) == 4 else "x"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _id(*parts) -> str:
    return str(uuid.uuid5(_NS, ":".join(str(p) for p in parts)))


def _auth_events(now: datetime) -> list[dict]:
    """Raw (unmasked) synthetic auth events, newest first. Internal only."""
    rng = random.Random("vigil-security-seed")
    events = []

    def add(minutes_ago: float, email: str, event_type: str, ip: str, ua: str):
        events.append({
            "email": email, "event_type": event_type, "ip_address": ip,
            "user_agent": ua, "created_at": now - timedelta(minutes=minutes_ago),
        })

    # Credential stuffing: one IP, 14 different accounts, within 2 minutes.
    for i in range(14):
        add(4 + i * 0.15, f"user{i + 1:02d}@example.com", "login_failure", STUFFING_IP, UA_SCRIPT)
    # Brute force: 7 failures on one account within 6 minutes.
    for i in range(7):
        add(14 + i * 0.9, BRUTE_TARGET, "login_failure", BRUTE_IP, UA_SCRIPT)
    # A normal day: sign-ins spread over 24 hours, a few typos.
    for i in range(40):
        minutes = rng.uniform(25, 24 * 60)
        email = rng.choice(TEAM)
        kind = "login_failure" if rng.random() < 0.1 else "login_success"
        add(minutes, email, kind, rng.choice(NORMAL_IPS), UA_BROWSER)
    add(130, "erin@acme-corp.io", "signup", rng.choice(NORMAL_IPS), UA_BROWSER)

    events.sort(key=lambda e: e["created_at"], reverse=True)
    for i, e in enumerate(events):
        e["id"] = _id("auth", i)
    return events


def _audit_entries(now: datetime) -> list[dict]:
    """Synthetic audit rows, newest first, IPs unmasked. Internal only."""
    rows = [
        (12,   "user.locked",        "user",     BRUTE_TARGET,             BRUTE_IP,      {}),
        (35,   "alert.triggered",    "glue_job", "customer-data-pipeline", NORMAL_IPS[0], {"anomaly_count": 1}),
        (52,   "user.login",         "user",     "admin@acme-corp.io",     NORMAL_IPS[0], {}),
        (130,  "user.signup",        "user",     "erin@acme-corp.io",      NORMAL_IPS[2], {}),
        (190,  "user.role_changed",  "user",     "bob@acme-corp.io",       NORMAL_IPS[0], {"from": "analyst", "to": "admin"}),
        (240,  "user.login",         "user",     "carol@acme-corp.io",     NORMAL_IPS[1], {}),
        (380,  "user.unlocked",      "user",     "dan@acme-corp.io",       NORMAL_IPS[0], {}),
        (600,  "user.login",         "user",     "bob@acme-corp.io",       NORMAL_IPS[3], {}),
        (900,  "role.permission_granted", "role", "analyst",               NORMAL_IPS[0], {"permission": "alerts:read"}),
        (1300, "user.login",         "user",     "dan@acme-corp.io",       NORMAL_IPS[2], {}),
    ]
    return [
        {
            "id":            _id("audit", i),
            "user_id":       _id("user", "admin@acme-corp.io"),
            "action":        action,
            "resource_type": rtype,
            "resource_id":   rid,
            "metadata":      meta,
            "ip_address":    ip,
            "user_agent":    UA_BROWSER,
            "created_at":    (now - timedelta(minutes=m)).isoformat(),
        }
        for i, (m, action, rtype, rid, ip, meta) in enumerate(rows)
    ]


def _mask_anomaly(a: dict) -> dict:
    out = dict(a, ip_address=mask_ip(a.get("ip_address")))
    if a.get("ip_address"):
        out["message"] = a["message"].replace(a["ip_address"], out["ip_address"])
    if isinstance(out.get("detected_at"), datetime):
        out["detected_at"] = out["detected_at"].isoformat()
    return out


# ── What the guest-facing endpoints return ───────────────────────────────────

def get_seed_auth_anomalies() -> list[dict]:
    """Run the real detection engine over the synthetic events, then mask."""
    return [_mask_anomaly(a) for a in detect_auth_anomalies(_auth_events(_now()))]


def get_seed_auth_events(event_type=None, email=None, page=1, page_size=50) -> dict:
    rows = _auth_events(_now())
    if event_type:
        rows = [r for r in rows if r["event_type"] == event_type]
    if email:
        rows = [r for r in rows if r["email"] == email.strip().lower()]
    start = (page - 1) * page_size
    return {
        "total": len(rows), "page": page, "page_size": page_size,
        "events": [
            {
                "id":         r["id"],
                "email":      r["email"],
                "user_id":    None,
                "event_type": r["event_type"],
                "ip_address": mask_ip(r["ip_address"]),
                "user_agent": r["user_agent"],
                "created_at": r["created_at"].isoformat(),
            }
            for r in rows[start:start + page_size]
        ],
        "source": "sample",
    }


def get_seed_audit_log(action=None, page=1, page_size=50) -> dict:
    rows = _audit_entries(_now())
    if action:
        rows = [r for r in rows if r["action"] == action]
    start = (page - 1) * page_size
    return {
        "total": len(rows), "page": page, "page_size": page_size,
        "entries": [dict(r, ip_address=mask_ip(r["ip_address"])) for r in rows[start:start + page_size]],
        "source": "sample",
    }


def get_seed_security_posture() -> dict:
    now = _now()
    events = [e for e in _auth_events(now) if e["created_at"] >= now - timedelta(hours=24)]

    hourly: dict = defaultdict(lambda: {"failures": 0, "successes": 0})
    failures_by_ip: dict = defaultdict(int)
    for e in events:
        key = e["created_at"].replace(minute=0, second=0, microsecond=0).strftime("%H:%M")
        if e["event_type"] == "login_failure":
            hourly[key]["failures"] += 1
            failures_by_ip[e["ip_address"]] += 1
        elif e["event_type"] == "login_success":
            hourly[key]["successes"] += 1

    login_activity = []
    for i in range(24):
        key = (now - timedelta(hours=23 - i)).replace(minute=0, second=0, microsecond=0).strftime("%H:%M")
        login_activity.append({"hour": key, **hourly[key]})

    top_ips = sorted(failures_by_ip.items(), key=lambda kv: kv[1], reverse=True)[:5]
    anomalies = detect_auth_anomalies(events)

    return {
        "login_activity":  login_activity,
        "top_ips":         [{"ip": mask_ip(ip), "failure_count": n} for ip, n in top_ips],
        "anomaly_summary": {
            "total":    len(anomalies),
            "critical": sum(1 for a in anomalies if a["severity"] == "critical"),
            "warning":  sum(1 for a in anomalies if a["severity"] == "warning"),
        },
        "users_by_role":   [{"role": "admin", "count": 2}, {"role": "analyst", "count": 4}],
        "locked_count":    1,
        "failures_24h":    sum(h["failures"] for h in login_activity),
        "security_events": [
            {k: r[k] for k in ("action", "resource_id", "ip_address", "created_at")}
            for r in get_seed_audit_log(page_size=10)["entries"]
        ],
        "source":          "sample",
    }
