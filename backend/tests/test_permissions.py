import uuid

import pytest
from conftest import auth_header

import permissions
from permissions import has_permission

ALERT = {"job_name": "customer-data-pipeline", "recipient_email": "oncall@example.com"}
SOMEONE = str(uuid.uuid4())

# Every route that changes state, other than login/signup/refresh/logout.
WRITE_ROUTES = [
    ("post",   "/api/v1/alerts/trigger",                           ALERT),
    ("post",   f"/api/v1/admin/users/{SOMEONE}/unlock",             None),
    ("delete", f"/api/v1/admin/users/{SOMEONE}/sessions",           None),
    ("patch",  f"/api/v1/admin/users/{SOMEONE}",                    {"role": "admin"}),
    ("post",   "/api/v1/admin/roles/guest/permissions/users:manage", None),
    ("delete", "/api/v1/admin/roles/analyst/permissions/jobs:read",  None),
    ("post",   "/api/v1/auth/totp/enroll",                         None),
    ("post",   "/api/v1/auth/totp/confirm",                        {"code": "123456"}),
    ("post",   "/api/v1/auth/totp/disable",                        {"code": "123456"}),
    ("post",   "/api/v1/auth/totp/backup-codes",                   None),
    ("delete", f"/api/v1/auth/sessions/{SOMEONE}",                  None),
]


def call(client, method, path, body, headers):
    kwargs = {"headers": headers}
    if body is not None:
        kwargs["json"] = body
    return getattr(client, method)(path, **kwargs)


def test_allowed_role_passes(client, make_user):
    res = client.get("/api/v1/glue/jobs", headers=auth_header(make_user("analyst")))
    assert res.status_code == 200


def test_admin_passes_a_guarded_write(client, make_user):
    res = client.post("/api/v1/alerts/trigger", json=ALERT, headers=auth_header(make_user("admin")))
    assert res.status_code == 200


def test_denied_role_gets_403(client, make_user):
    analyst = auth_header(make_user("analyst"))
    assert client.post("/api/v1/alerts/trigger", json=ALERT, headers=analyst).status_code == 403
    assert client.get("/api/v1/admin/users", headers=analyst).status_code == 403


def test_no_token_gets_401(client):
    assert client.get("/api/v1/glue/jobs").status_code == 401


@pytest.mark.parametrize("method,path,body", WRITE_ROUTES, ids=[f"{m} {p}" for m, p, _ in WRITE_ROUTES])
def test_guest_is_blocked_from_every_write_route(client, guest_headers, method, path, body):
    assert call(client, method, path, body, guest_headers).status_code == 403


def test_guest_write_attempts_change_nothing(client, guest_headers, db):
    for method, path, body in WRITE_ROUTES:
        call(client, method, path, body, guest_headers)
    permissions.invalidate_cache()  # read the role table, not a cached copy
    assert has_permission("analyst", "jobs:read", db)
    assert not has_permission("guest", "users:manage", db)


def test_guest_can_read_pipeline_data(client, guest_headers):
    assert client.get("/api/v1/glue/jobs", headers=guest_headers).status_code == 200
    assert client.get("/api/v1/anomalies/summary", headers=guest_headers).status_code == 200
