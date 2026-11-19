"""DATA_SOURCE=seed: no AWS, no real email."""
import os
import subprocess
import sys
from unittest import mock

from conftest import BACKEND, auth_header
from models import AlertLog

ALERT = {"job_name": "customer-data-pipeline", "recipient_email": "oncall@example.com"}


def test_app_boots_without_aws_env_vars_or_boto3():
    """Import the app in a fresh interpreter with no AWS settings at all."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("AWS_")}
    env.pop("DATA_SOURCE", None)  # the default must be seed
    code = (
        "import dotenv; dotenv.load_dotenv = lambda *a, **k: False\n"
        "import sys, main, settings\n"
        "assert settings.DATA_SOURCE == 'seed', settings.DATA_SOURCE\n"
        "assert 'boto3' not in sys.modules, 'boto3 was imported'\n"
    )
    result = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, env=env,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_alert_scan_does_not_call_sendgrid(client, make_user, db):
    with mock.patch("sendgrid.SendGridAPIClient") as sendgrid_client:
        res = client.post("/api/v1/alerts/trigger", json=ALERT, headers=auth_header(make_user("admin")))

    assert res.status_code == 200
    body = res.json()
    assert body["sent"] is True and body["simulated"] is True
    assert body["anomaly_count"] > 0
    sendgrid_client.assert_not_called()

    log = db.query(AlertLog).one()
    assert log.simulated is True and log.sendgrid_status is None


def test_deep_health_skips_aws(client):
    res = client.get("/health/deep")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "healthy" and body["data_source"] == "seed"
    assert body["checks"]["database"]["status"] == "ok"
    aws_checks = {k: v["status"] for k, v in body["checks"].items() if k != "database"}
    assert aws_checks and set(aws_checks.values()) == {"skipped"}


def test_seed_jobs_are_served(client, make_user):
    res = client.get("/api/v1/glue/jobs", headers=auth_header(make_user()))
    assert res.status_code == 200
    assert "customer-data-pipeline" in {j["name"] for j in res.json()["jobs"]}
