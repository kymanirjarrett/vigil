"""Synthetic security data for the shared guest account.

Real auth events and audit rows are never shown to the guest. IPs here are
from the documentation ranges (RFC 5737), so they belong to nobody.
"""
from datetime import datetime, timedelta, timezone


def get_seed_security_posture() -> dict:
    """
    Pre-built security posture snapshot shown to the shared guest account.
    Story: credential-stuffing attack hit ~3 hours ago, one account locked.
    """
    now = datetime.now(timezone.utc)

    # 24-hour login activity — attack spike at hour index 20 (~3 h ago)
    login_activity = []
    for i in range(24):
        h   = (now - timedelta(hours=23 - i)).replace(minute=0, second=0, microsecond=0)
        key = h.strftime("%H:%M")
        if i < 8:
            failures, successes = 0, 0
        elif i == 20:                   # attack peak
            failures, successes = 47, 3
        elif i == 19 or i == 21:        # before/after the peak
            failures, successes = 8, 6
        else:
            failures, successes = 1 if i % 3 == 0 else 0, 4 + (i % 5)
        login_activity.append({"hour": key, "failures": failures, "successes": successes})

    return {
        "login_activity": login_activity,
        "top_ips": [
            {"ip": "203.0.113.45",  "failure_count": 47},
            {"ip": "198.51.100.23", "failure_count": 8},
            {"ip": "192.0.2.178",   "failure_count": 3},
        ],
        "anomaly_summary": {"total": 2, "critical": 1, "warning": 1},
        "users_by_role": [
            {"role": "admin",   "count": 1},
            {"role": "analyst", "count": 3},
        ],
        "locked_count": 1,
        "failures_24h": 62,
        "security_events": [
            {
                "action": "user.locked",
                "resource_id": "alice@acme-corp.io",
                "ip_address": "203.0.113.45",
                "created_at": (now - timedelta(minutes=8)).isoformat(),
            },
            {
                "action": "user.login",
                "resource_id": "admin@vigil.io",
                "ip_address": "10.0.0.1",
                "created_at": (now - timedelta(minutes=30)).isoformat(),
            },
            {
                "action": "user.signup",
                "resource_id": "bob@acme-corp.io",
                "ip_address": "172.16.0.5",
                "created_at": (now - timedelta(hours=2)).isoformat(),
            },
            {
                "action": "user.login",
                "resource_id": "carol@acme-corp.io",
                "ip_address": "10.0.0.8",
                "created_at": (now - timedelta(hours=4)).isoformat(),
            },
        ],
        "source": "sample",
    }


def get_seed_auth_anomalies() -> list[dict]:
    """
    Pre-computed findings so the Threat Detection page always tells a story.
    Two scenarios:
      - Credential stuffing: 14 accounts targeted from a single IP
      - Brute force: 7 rapid failures against one account
    """
    now = datetime.now(timezone.utc)
    return [
        {
            "type":        "CREDENTIAL_STUFFING",
            "severity":    "critical",
            "email":       None,
            "ip_address":  "203.0.113.45",
            "message":     (
                "Login failures targeting 14 unique accounts from "
                "203.0.113.45 within 5 minutes."
            ),
            "detected_at": (now - timedelta(minutes=3)).isoformat(),
        },
        {
            "type":        "BRUTE_FORCE",
            "severity":    "warning",
            "email":       "alice@acme-corp.io",
            "ip_address":  None,
            "message":     (
                "7 failed login attempts for alice@acme-corp.io "
                "within 10 minutes."
            ),
            "detected_at": (now - timedelta(minutes=8)).isoformat(),
        },
    ]
