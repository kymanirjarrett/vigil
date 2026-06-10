import os
from datetime import datetime, timedelta, timezone
from collections import defaultdict

BRUTE_FORCE_THRESHOLD        = int(os.getenv("BRUTE_FORCE_THRESHOLD",        "5"))
BRUTE_FORCE_WINDOW_MINUTES   = int(os.getenv("BRUTE_FORCE_WINDOW_MINUTES",   "10"))
CRED_STUFFING_THRESHOLD      = int(os.getenv("CRED_STUFFING_THRESHOLD",      "10"))
CRED_STUFFING_WINDOW_MINUTES = int(os.getenv("CRED_STUFFING_WINDOW_MINUTES", "5"))


def _as_utc(ts) -> datetime:
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def detect_brute_force(events: list, threshold: int, window_minutes: int) -> list:
    """
    Flag any account (email) that accumulates >= threshold login_failure events
    within a rolling window_minutes window.
    """
    failures = [e for e in events if e.get("event_type") == "login_failure"]

    by_email = defaultdict(list)
    for e in failures:
        by_email[e["email"]].append(_as_utc(e["created_at"]))

    detected = []
    for email, timestamps in by_email.items():
        timestamps.sort()
        for i, ts in enumerate(timestamps):
            window_end = ts + timedelta(minutes=window_minutes)
            count = sum(1 for t in timestamps[i:] if t <= window_end)
            if count >= threshold:
                detected.append({
                    "type":        "BRUTE_FORCE",
                    "severity":    "warning",
                    "email":       email,
                    "ip_address":  None,
                    "message":     (
                        f"{count} failed login attempts for {email} "
                        f"within {window_minutes} minutes."
                    ),
                    "detected_at": timestamps[-1].isoformat(),
                })
                break  # one finding per email per scan

    return detected


def detect_credential_stuffing(events: list, threshold: int, window_minutes: int) -> list:
    """
    Flag any source IP that targets >= threshold distinct accounts with login failures
    within a rolling window_minutes window — characteristic of credential-stuffing.
    """
    failures = [
        e for e in events
        if e.get("event_type") == "login_failure" and e.get("ip_address")
    ]

    by_ip = defaultdict(list)
    for e in failures:
        by_ip[e["ip_address"]].append(e)

    detected = []
    for ip, ip_events in by_ip.items():
        ip_events = sorted(ip_events, key=lambda e: _as_utc(e["created_at"]))
        for i, evt in enumerate(ip_events):
            window_end = _as_utc(evt["created_at"]) + timedelta(minutes=window_minutes)
            window_events = [e for e in ip_events[i:] if _as_utc(e["created_at"]) <= window_end]
            unique_emails = len({e["email"] for e in window_events})
            if unique_emails >= threshold:
                last_ts = _as_utc(ip_events[-1]["created_at"])
                detected.append({
                    "type":        "CREDENTIAL_STUFFING",
                    "severity":    "critical",
                    "email":       None,
                    "ip_address":  ip,
                    "message":     (
                        f"Login failures targeting {unique_emails} unique accounts "
                        f"from {ip} within {window_minutes} minutes."
                    ),
                    "detected_at": last_ts.isoformat(),
                })
                break  # one finding per IP per scan

    return detected


def detect_auth_anomalies(events: list) -> list:
    """
    Run all auth detection rules over a list of auth event dicts.
    Each dict must have: event_type, email, ip_address, created_at.
    Returns findings sorted newest-first.
    """
    results = (
        detect_brute_force(events, BRUTE_FORCE_THRESHOLD, BRUTE_FORCE_WINDOW_MINUTES)
        + detect_credential_stuffing(events, CRED_STUFFING_THRESHOLD, CRED_STUFFING_WINDOW_MINUTES)
    )
    return sorted(results, key=lambda a: a["detected_at"], reverse=True)
