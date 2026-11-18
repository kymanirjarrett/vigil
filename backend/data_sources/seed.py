"""Deterministic sample pipeline data (DATA_SOURCE=seed, the default).

Runs are laid out backwards from the current hour, so the data always looks
recent. Durations come from a per-job random generator with a fixed seed and
run IDs are hashes of (job, run index), so the output is identical within each
10-minute window.

The story the anomaly engine finds:
  customer-data-pipeline  two most recent runs FAILED   -> CONSECUTIVE_FAILURES
  ml-feature-extraction   yesterday's run ran ~6x long  -> DURATION_SPIKE
  legacy-etl-migration    isolated failures only        -> nothing (by design)
  revenue-aggregation     hourly and healthy, one run in progress
"""
import hashlib
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy.orm import Session

from anomaly_detection import detect_anomalies
from data_sources.base import DataProvider, JobNotFoundError


@dataclass(frozen=True)
class _JobSpec:
    name: str
    glue_version: str
    worker_type: str
    max_capacity: int
    timeout: int
    created_days_ago: int
    modified_days_ago: int
    interval_hours: int
    base_seconds: int
    jitter: float          # max +/- fraction of base_seconds
    run_count: int
    # run index (0 = newest) -> ("FAILED", error) | ("SPIKE", factor) | ("RUNNING",)
    events: dict = field(default_factory=dict)


_JOBS = [
    _JobSpec(
        name="customer-data-pipeline", glue_version="4.0", worker_type="G.1X",
        max_capacity=10, timeout=2880, created_days_ago=180, modified_days_ago=1,
        interval_hours=24, base_seconds=480, jitter=0.08, run_count=20,
        events={
            0: ("FAILED", "Connection timeout: upstream CRM API unresponsive"),
            1: ("FAILED", "Connection timeout: upstream CRM API unresponsive"),
            9: ("FAILED", "Job bookmark error: invalid state"),
        },
    ),
    _JobSpec(
        name="revenue-aggregation", glue_version="4.0", worker_type="G.1X",
        max_capacity=5, timeout=1440, created_days_ago=365, modified_days_ago=7,
        interval_hours=1, base_seconds=600, jitter=0.08, run_count=24,
        events={0: ("RUNNING",)},
    ),
    _JobSpec(
        name="ml-feature-extraction", glue_version="4.0", worker_type="G.2X",
        max_capacity=20, timeout=2880, created_days_ago=90, modified_days_ago=3,
        interval_hours=24, base_seconds=800, jitter=0.06, run_count=20,
        events={
            1: ("SPIKE", 6.5),
            10: ("FAILED", "Out of memory: executor lost on worker node"),
        },
    ),
    _JobSpec(
        name="legacy-etl-migration", glue_version="3.0", worker_type="Standard",
        max_capacity=5, timeout=4320, created_days_ago=730, modified_days_ago=14,
        interval_hours=24, base_seconds=900, jitter=0.05, run_count=20,
        events={
            3: ("FAILED", "Schema mismatch: column 'legacy_id' not found"),
            11: ("FAILED", "Connection pool exhausted"),
        },
    ),
]
_JOBS_BY_NAME = {j.name: j for j in _JOBS}


def _ts(dt: datetime) -> str:
    # Same string format the AWS provider produces (str() of a tz-aware datetime).
    return str(dt)


def _run_id(job: str, index: int) -> str:
    return "jr_" + hashlib.sha256(f"{job}:{index}".encode()).hexdigest()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SeedDataProvider(DataProvider):
    name = "seed"

    def __init__(self, now: Callable[[], datetime] = _utc_now):
        self._now = now

    def _anchor(self) -> datetime:
        # Newest run started 5 to 15 minutes ago. Flooring to 10 minutes keeps
        # the output identical within each 10-minute window.
        now = self._now()
        floored = now.replace(minute=now.minute - now.minute % 10, second=0, microsecond=0)
        return floored - timedelta(minutes=5)

    def _build_runs(self, spec: _JobSpec) -> list[dict]:
        rng = random.Random(spec.name)  # fixed seed per job
        # Evenly spaced offsets in a shuffled order, not independent random
        # draws: random draws can land 2+ sample standard deviations out and
        # trip the spike rule by chance. Evenly spaced values stay under about
        # 1.73 standard deviations, so only the engineered events are anomalies.
        n = spec.run_count
        offsets = [-spec.jitter + 2 * spec.jitter * k / (n - 1) for k in range(n)]
        rng.shuffle(offsets)
        anchor = self._anchor()
        runs = []
        for i in range(n):
            started = anchor - timedelta(hours=i * spec.interval_hours)
            seconds = round(spec.base_seconds * (1 + offsets[i]))
            event = spec.events.get(i, ())
            kind = event[0] if event else "SUCCEEDED"

            status, error = "SUCCEEDED", None
            if kind == "FAILED":
                status, error = "FAILED", event[1]
                seconds = rng.randint(30, 120)  # failed early
            elif kind == "SPIKE":
                seconds = round(spec.base_seconds * event[1])
            elif kind == "RUNNING":
                status = "RUNNING"

            done = status != "RUNNING"
            runs.append({
                "run_id":         _run_id(spec.name, i),
                "status":         status,
                "started_on":     _ts(started),
                "completed_on":   _ts(started + timedelta(seconds=seconds)) if done else "",
                "execution_time": seconds if done else 0,
                "error_message":  error,
                "dpu_seconds":    seconds * spec.max_capacity if status == "SUCCEEDED" else None,
            })
        return runs

    # ── DataProvider ────────────────────────────────────────────────────────

    def list_jobs(self) -> list[dict]:
        now = self._now()
        return [
            {
                "name":          j.name,
                "created_on":    _ts(now - timedelta(days=j.created_days_ago)),
                "last_modified": _ts(now - timedelta(days=j.modified_days_ago)),
                "glue_version":  j.glue_version,
                "worker_type":   j.worker_type,
                "max_capacity":  j.max_capacity,
                "timeout":       j.timeout,
            }
            for j in _JOBS
        ]

    def get_runs(self, job_name: str, max_results: int = 50) -> list[dict]:
        spec = _JOBS_BY_NAME.get(job_name)
        if spec is None:
            raise JobNotFoundError(job_name)
        return self._build_runs(spec)[:max_results]

    def record_anomalies(self, db: Session, anomalies: list[dict]) -> None:
        # History is derived from the seed runs on read, so it stays current
        # and the shared database never fills with sample rows.
        return None

    def anomaly_history(self, db: Session, limit: int) -> list[dict]:
        history = []
        for spec in _JOBS:
            runs = {r["run_id"]: r for r in self._build_runs(spec)}
            for a in detect_anomalies(list(runs.values())):
                run = runs[a["run_id"]]
                history.append({
                    "job_name":    spec.name,
                    "run_id":      a["run_id"],
                    "type":        a["type"],
                    "severity":    a["severity"],
                    "message":     a["message"],
                    # isoformat() to match the AWS provider's DB-backed history
                    "detected_at": datetime.fromisoformat(
                        run["completed_on"] or run["started_on"]
                    ).isoformat(),
                })
        history.sort(key=lambda h: h["detected_at"], reverse=True)
        for i, h in enumerate(history, start=1):
            h["id"] = i
        return history[:limit]

    def health_checks(self) -> dict[str, dict]:
        skipped = {"status": "skipped", "detail": "DATA_SOURCE=seed"}
        return {
            "glue":               dict(skipped),
            "s3_athena_results":  dict(skipped),
            "glue_catalog_table": dict(skipped),
        }
