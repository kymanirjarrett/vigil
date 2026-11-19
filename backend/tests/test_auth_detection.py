from datetime import datetime, timedelta, timezone

from auth_detection import detect_brute_force, detect_credential_stuffing
from models import AuthEvent

NOW = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)


def failure(email, ip="198.51.100.1", minutes_ago=0.0):
    return {"event_type": "login_failure", "email": email, "ip_address": ip,
            "created_at": NOW - timedelta(minutes=minutes_ago)}


def test_brute_force_repeated_failures_on_one_account():
    events = [failure("alice@example.com", minutes_ago=i) for i in range(5)]
    found = detect_brute_force(events, threshold=5, window_minutes=10)
    assert [(a["type"], a["email"]) for a in found] == [("BRUTE_FORCE", "alice@example.com")]


def test_brute_force_ignores_failures_spread_outside_the_window():
    events = [failure("alice@example.com", minutes_ago=i * 5) for i in range(5)]
    assert detect_brute_force(events, threshold=5, window_minutes=10) == []


def test_credential_stuffing_many_accounts_from_one_ip():
    events = [failure(f"user{i}@example.com", ip="203.0.113.9", minutes_ago=i * 0.1)
              for i in range(10)]
    found = detect_credential_stuffing(events, threshold=10, window_minutes=5)
    assert [(a["type"], a["ip_address"]) for a in found] == [("CREDENTIAL_STUFFING", "203.0.113.9")]


def test_many_accounts_from_different_ips_is_not_stuffing():
    events = [failure(f"user{i}@example.com", ip=f"203.0.113.{i}") for i in range(10)]
    assert detect_credential_stuffing(events, threshold=10, window_minutes=5) == []


def test_failures_for_nonexistent_emails_are_recorded(client, db):
    res = client.post("/api/v1/auth/login",
                      json={"email": "Nobody@Example.com", "password": "whatever-123"})
    assert res.status_code == 401
    rows = db.query(AuthEvent).all()
    assert [(r.email, r.event_type, r.user_id) for r in rows] == [
        ("nobody@example.com", "login_failure", None)
    ]
