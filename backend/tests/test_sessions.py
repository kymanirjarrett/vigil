"""Refresh-token rotation and reuse detection, and account lockout."""
from datetime import UTC, datetime, timedelta

from conftest import PASSWORD

from models import RefreshToken

LOGIN   = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"


def login(client, email, password=PASSWORD):
    return client.post(LOGIN, json={"email": email, "password": password})


def refresh(client, token):
    return client.post(REFRESH, json={"refresh_token": token})


# ── Refresh tokens ────────────────────────────────────────────────────────────

def test_rotation_issues_a_new_token_and_retires_the_old(client, make_user):
    user = make_user()
    first = login(client, user.email).json()["refresh_token"]

    res = refresh(client, first)
    assert res.status_code == 200
    second = res.json()["refresh_token"]
    assert second != first
    assert refresh(client, second).status_code == 200


def test_reusing_a_rotated_token_revokes_its_whole_family(client, make_user, db):
    user = make_user()
    stolen = login(client, user.email).json()["refresh_token"]
    current = refresh(client, stolen).json()["refresh_token"]

    res = refresh(client, stolen)  # replayed by an attacker
    assert res.status_code == 401
    assert "reuse" in res.json()["detail"].lower()
    # The legitimate holder's newer token is revoked too.
    assert refresh(client, current).status_code == 401


def test_reuse_revocation_is_scoped_to_one_session_chain(client, make_user, db):
    """Reuse revokes the compromised chain (the token family), not the user's
    other devices. This matters for the shared guest: one visitor replaying a
    token must not sign every other visitor out."""
    user = make_user()
    laptop = login(client, user.email).json()["refresh_token"]
    phone  = login(client, user.email).json()["refresh_token"]

    refresh(client, laptop)
    refresh(client, laptop)  # reuse on the laptop chain

    assert refresh(client, phone).status_code == 200


def test_expired_refresh_token_is_rejected(client, make_user, db):
    user = make_user()
    raw = login(client, user.email).json()["refresh_token"]
    db.query(RefreshToken).update({"expires_at": datetime.now(UTC) - timedelta(seconds=1)})
    db.commit()
    assert refresh(client, raw).status_code == 401


# ── Lockout ───────────────────────────────────────────────────────────────────

def test_locks_after_threshold_then_unlocks_after_cooldown(client, make_user, db):
    user = make_user("analyst")
    for _ in range(5):
        assert login(client, user.email, "wrong-password").status_code == 401

    # Locked: even the right password is refused.
    assert login(client, user.email).status_code == 429
    db.refresh(user)
    assert user.locked_until > datetime.now(UTC)

    # Cooldown passes.
    user.locked_until = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    assert login(client, user.email).status_code == 200
    db.refresh(user)
    assert user.locked_until is None


def test_below_threshold_does_not_lock(client, make_user):
    user = make_user("analyst")
    for _ in range(4):
        login(client, user.email, "wrong-password")
    assert login(client, user.email).status_code == 200


def test_admins_are_never_locked_out(client, make_user):
    admin = make_user("admin")
    for _ in range(6):
        login(client, admin.email, "wrong-password")
    assert login(client, admin.email).status_code == 200


def test_login_rate_limit_returns_429(client, make_user):
    from routers.auth import limiter
    limiter.reset()
    limiter.enabled = True
    codes = [login(client, "nobody@example.com", "x" * 8).status_code for _ in range(6)]
    assert codes[:5] == [401] * 5
    assert codes[5] == 429
