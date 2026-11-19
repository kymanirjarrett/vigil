"""Live AWS Glue data (DATA_SOURCE=aws). Off by default.

This is the only module that imports boto3, and it is only imported when
DATA_SOURCE=aws, so the app boots without AWS credentials or network access.
Clients are created on first use, never at import time.
"""
import os
from functools import cached_property

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from data_sources.base import DataProvider, DataSourceError, JobNotFoundError
from models import AnomalyEvent


def _map_run(run: dict) -> dict:
    return {
        "run_id":         run["Id"],
        "status":         run["JobRunState"],
        "started_on":     str(run.get("StartedOn", "")),
        "completed_on":   str(run.get("CompletedOn", "")),
        "execution_time": run.get("ExecutionTime", 0),
        "error_message":  run.get("ErrorMessage"),
        "dpu_seconds":    run.get("DPUSeconds"),
    }


def _map_job(job: dict) -> dict:
    return {
        "name":          job["Name"],
        "created_on":    str(job.get("CreatedOn", "")),
        "last_modified": str(job.get("LastModifiedOn", "")),
        "glue_version":  job.get("GlueVersion", "N/A"),
        "worker_type":   job.get("WorkerType", "N/A"),
        "max_capacity":  job.get("MaxCapacity", "N/A"),
        "timeout":       job.get("Timeout", "N/A"),
    }


def _error_detail(exc: Exception) -> str:
    if isinstance(exc, ClientError):
        return exc.response["Error"]["Message"]
    return str(exc)


class AwsDataProvider(DataProvider):
    name = "aws"

    def __init__(self):
        self.region         = os.getenv("AWS_REGION", "us-east-2")
        self.glue_database  = os.getenv("GLUE_DATABASE_NAME", "")
        self.glue_table     = os.getenv("GLUE_TABLE_NAME", "vigil_sales_daily")
        self.athena_bucket  = os.getenv("ATHENA_RESULTS_BUCKET", "")

    def _client(self, service: str):
        # boto3 reads AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY from the
        # environment through its default credential chain.
        return boto3.client(service, region_name=self.region)

    @cached_property
    def glue(self):
        return self._client("glue")

    @cached_property
    def s3(self):
        return self._client("s3")

    # ── DataProvider ────────────────────────────────────────────────────────

    def list_jobs(self) -> list[dict]:
        try:
            return [_map_job(j) for j in self.glue.get_jobs().get("Jobs", [])]
        except (ClientError, BotoCoreError) as exc:
            raise DataSourceError(_error_detail(exc)) from exc

    def get_runs(self, job_name: str, max_results: int = 50) -> list[dict]:
        try:
            resp = self.glue.get_job_runs(JobName=job_name, MaxResults=max_results)
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "EntityNotFoundException":
                raise JobNotFoundError(job_name) from exc
            raise DataSourceError(_error_detail(exc)) from exc
        except BotoCoreError as exc:
            raise DataSourceError(_error_detail(exc)) from exc
        return [_map_run(r) for r in resp.get("JobRuns", [])]

    def record_anomalies(self, db: Session, anomalies: list[dict]) -> None:
        # (run_id, type) is unique, so re-scanning the same runs is a no-op.
        for a in anomalies:
            db.add(AnomalyEvent(
                job_name=a["job_name"], run_id=a["run_id"], type=a["type"],
                severity=a["severity"], message=a["message"],
            ))
            try:
                db.commit()
            except IntegrityError:
                db.rollback()

    def anomaly_history(self, db: Session, limit: int) -> list[dict]:
        rows = (
            db.query(AnomalyEvent)
              .order_by(AnomalyEvent.detected_at.desc())
              .limit(limit)
              .all()
        )
        return [
            {
                "id":          r.id,
                "job_name":    r.job_name,
                "run_id":      r.run_id,
                "type":        r.type,
                "severity":    r.severity,
                "message":     r.message,
                "detected_at": r.detected_at.isoformat() if r.detected_at else None,
            }
            for r in rows
        ]

    def health_checks(self) -> dict[str, dict]:
        return {
            "glue":               self._check(lambda: self.glue.get_jobs(MaxResults=1)),
            "s3_athena_results":  self._check_athena_bucket(),
            "glue_catalog_table": self._check_catalog_table(),
        }

    # ── health helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _check(call, **ok_fields) -> dict:
        try:
            call()
            return {"status": "ok", **ok_fields}
        except Exception as exc:  # health checks report, never raise
            return {"status": "error", "detail": _error_detail(exc)}

    def _check_athena_bucket(self) -> dict:
        if not self.athena_bucket:
            return {"status": "unconfigured", "detail": "ATHENA_RESULTS_BUCKET not set"}
        return self._check(lambda: self.s3.head_bucket(Bucket=self.athena_bucket),
                           bucket=self.athena_bucket)

    def _check_catalog_table(self) -> dict:
        if not self.glue_database:
            return {"status": "unconfigured", "detail": "GLUE_DATABASE_NAME not set"}
        try:
            self.glue.get_table(DatabaseName=self.glue_database, Name=self.glue_table)
            return {"status": "ok", "database": self.glue_database, "table": self.glue_table}
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "EntityNotFoundException":
                return {"status": "error",
                        "detail": f"Table {self.glue_database}.{self.glue_table} not found"}
            return {"status": "error", "detail": _error_detail(exc)}
        except Exception as exc:
            return {"status": "error", "detail": _error_detail(exc)}
