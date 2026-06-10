from datetime import datetime, timedelta, timezone
import uuid

_NOW = datetime.now(timezone.utc)


def _dt(days_ago: int, hour: int = 8) -> datetime:
    return (_NOW - timedelta(days=days_ago)).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )


def _run(status: str, days_ago: int, hour: int, execution_time: int, error: str = None) -> dict:
    started = _dt(days_ago, hour)
    completed = started + timedelta(seconds=execution_time) if execution_time else started
    return {
        "run_id": str(uuid.uuid4()),
        "status": status,
        "started_on": str(started),
        "completed_on": str(completed),
        "execution_time": execution_time,
        "error_message": error,
        "dpu_seconds": execution_time * 2 if status == "SUCCEEDED" else None,
    }


DEMO_JOBS = [
    {
        "name": "customer-data-pipeline",
        "created_on": str(_dt(180)),
        "last_modified": str(_dt(1)),
        "glue_version": "3.0",
        "worker_type": "G.1X",
        "max_capacity": 10,
        "timeout": 2880,
    },
    {
        "name": "revenue-aggregation",
        "created_on": str(_dt(365)),
        "last_modified": str(_dt(7)),
        "glue_version": "4.0",
        "worker_type": "G.1X",
        "max_capacity": 5,
        "timeout": 1440,
    },
    {
        "name": "ml-feature-extraction",
        "created_on": str(_dt(90)),
        "last_modified": str(_dt(3)),
        "glue_version": "3.0",
        "worker_type": "G.2X",
        "max_capacity": 20,
        "timeout": 2880,
    },
    {
        "name": "legacy-etl-migration",
        "created_on": str(_dt(730)),
        "last_modified": str(_dt(14)),
        "glue_version": "2.0",
        "worker_type": "Standard",
        "max_capacity": 5,
        "timeout": 4320,
    },
]

# Runs are newest-first (mirrors AWS Glue API order).
# Anomalies engineered:
#   customer-data-pipeline  → 2 consecutive failures at top  (CONSECUTIVE_FAILURES)
#   ml-feature-extraction   → one 5400s spike vs ~800s avg   (DURATION_SPIKE)
#   legacy-etl-migration    → one 4200s spike vs ~900s avg   (DURATION_SPIKE)
#   revenue-aggregation     → clean baseline, no anomalies
_DEMO_RUNS: dict[str, list[dict]] = {
    "customer-data-pipeline": [
        _run("FAILED",    0,  8,    0, "Connection timeout: upstream CRM API unresponsive"),
        _run("FAILED",    1,  8,    0, "Connection timeout: upstream CRM API unresponsive"),
        _run("SUCCEEDED", 2,  8,  480),
        _run("SUCCEEDED", 3,  8,  510),
        _run("SUCCEEDED", 4,  8,  455),
        _run("SUCCEEDED", 5,  8,  490),
        _run("SUCCEEDED", 6,  8,  470),
        _run("FAILED",    7,  8,    0, "Job bookmark error: invalid state"),
        _run("SUCCEEDED", 8,  8,  500),
        _run("SUCCEEDED", 9,  8,  465),
        _run("SUCCEEDED", 10, 8,  520),
        _run("SUCCEEDED", 11, 8,  445),
        _run("SUCCEEDED", 12, 8,  495),
        _run("SUCCEEDED", 13, 8,  480),
        _run("SUCCEEDED", 14, 8,  510),
    ],
    "revenue-aggregation": [
        _run("SUCCEEDED", 0,  9,  85),
        _run("SUCCEEDED", 0, 10,  82),
        _run("SUCCEEDED", 0, 11,  88),
        _run("SUCCEEDED", 0, 12,  79),
        _run("SUCCEEDED", 0, 13,  91),
        _run("SUCCEEDED", 1,  9,  84),
        _run("SUCCEEDED", 1, 10,  87),
        _run("SUCCEEDED", 1, 11,  83),
        _run("SUCCEEDED", 1, 12,  90),
        _run("SUCCEEDED", 1, 13,  86),
        _run("SUCCEEDED", 2,  9,  81),
        _run("SUCCEEDED", 2, 10,  89),
        _run("SUCCEEDED", 2, 11,  85),
        _run("SUCCEEDED", 2, 12,  83),
        _run("SUCCEEDED", 2, 13,  88),
    ],
    "ml-feature-extraction": [
        _run("SUCCEEDED", 0,  2,  840),
        _run("SUCCEEDED", 1,  2,  780),
        _run("SUCCEEDED", 2,  2, 5400),  # spike — ~6.6σ above mean
        _run("SUCCEEDED", 3,  2,  820),
        _run("SUCCEEDED", 4,  2,  810),
        _run("SUCCEEDED", 5,  2,  760),
        _run("SUCCEEDED", 6,  2,  830),
        _run("SUCCEEDED", 7,  2,  800),
        _run("FAILED",    8,  2,    0, "Out of memory: executor lost on worker node"),
        _run("SUCCEEDED", 9,  2,  815),
        _run("SUCCEEDED", 10, 2,  790),
        _run("SUCCEEDED", 11, 2,  825),
    ],
    "legacy-etl-migration": [
        _run("SUCCEEDED", 0,  6,  920),
        _run("SUCCEEDED", 1,  6,  880),
        _run("FAILED",    2,  6,    0, "Schema mismatch: column 'legacy_id' not found"),
        _run("SUCCEEDED", 3,  6, 4200),  # spike
        _run("SUCCEEDED", 4,  6,  870),
        _run("SUCCEEDED", 5,  6,  910),
        _run("SUCCEEDED", 6,  6,  895),
        _run("SUCCEEDED", 7,  6,  860),
        _run("SUCCEEDED", 8,  6,  900),
        _run("FAILED",    9,  6,    0, "Connection pool exhausted"),
        _run("SUCCEEDED", 10, 6,  880),
        _run("SUCCEEDED", 11, 6,  915),
    ],
}


def get_demo_jobs() -> list[dict]:
    return DEMO_JOBS


def get_demo_runs(job_name: str) -> list[dict]:
    return _DEMO_RUNS.get(job_name, [])


def get_demo_auth_anomalies() -> list[dict]:
    """
    Pre-computed demo findings so the Threat Detection page always tells a story.
    Two scenarios:
      - Credential stuffing: 14 accounts targeted from a single IP
      - Brute force: 7 rapid failures against one account
    """
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
            "detected_at": (_NOW - timedelta(minutes=3)).isoformat(),
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
            "detected_at": (_NOW - timedelta(minutes=8)).isoformat(),
        },
    ]
