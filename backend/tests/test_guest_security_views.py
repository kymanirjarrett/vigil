"""The guest sees synthetic security data with masked IPs, never real rows."""
import re

import pytest

from conftest import PASSWORD, auth_header
from security_seed import mask_ip

SECURITY_VIEWS = [
    "/api/v1/auth-events",
    "/api/v1/auth-anomalies",
    "/api/v1/audit",
    "/api/v1/security/posture",
]

FULL_IPV4 = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
REAL_IP = "192.168.77.123"


@pytest.fixture
def real_activity(client, make_user):
    """A real sign-in from a known IP, so a leak would be visible."""
    user = make_user("analyst", email="real.person@example.com")
    res = client.post("/api/v1/auth/login", json={"email": user.email, "password": PASSWORD},
                      headers={"X-Forwarded-For": REAL_IP})
    assert res.status_code == 200
    return user


@pytest.mark.parametrize("path", SECURITY_VIEWS)
def test_guest_views_contain_no_unmasked_ip(client, guest_headers, real_activity, path):
    res = client.get(path, headers=guest_headers)
    assert res.status_code == 200
    assert FULL_IPV4.findall(res.text) == []
    assert REAL_IP not in res.text
    assert real_activity.email not in res.text


@pytest.mark.parametrize("path", ["/api/v1/auth-events", "/api/v1/audit", "/api/v1/security/posture"])
def test_guest_views_are_labelled_sample(client, guest_headers, path):
    assert client.get(path, headers=guest_headers).json()["source"] == "sample"


def test_admin_sees_real_rows(client, make_user, real_activity):
    res = client.get("/api/v1/auth-events", headers=auth_header(make_user("admin")))
    assert res.status_code == 200
    assert REAL_IP in res.text


def test_analyst_cannot_see_security_views(client, make_user):
    headers = auth_header(make_user("analyst"))
    for path in SECURITY_VIEWS:
        assert client.get(path, headers=headers).status_code == 403


@pytest.mark.parametrize("raw,masked", [
    ("203.0.113.45", "203.0.113.x"),
    ("2001:db8:1::5", "2001:db8:1:x"),
    (None, None),
    ("garbage", "x"),
])
def test_mask_ip(raw, masked):
    assert mask_ip(raw) == masked
