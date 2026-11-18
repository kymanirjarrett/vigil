"""The contract every pipeline data source implements.

Routers depend on this interface only. Which implementation they get is decided
once, by the DATA_SOURCE setting, in data_sources.get_data_provider().
"""
from abc import ABC, abstractmethod

from sqlalchemy.orm import Session


class JobNotFoundError(Exception):
    """The requested job does not exist in this data source."""


class DataSourceError(Exception):
    """The upstream data source failed (e.g. an AWS API error)."""


class DataProvider(ABC):
    #: Short identifier returned to clients as "source" ("seed" or "aws").
    name: str

    @abstractmethod
    def list_jobs(self) -> list[dict]:
        """All jobs: name, created_on, last_modified, glue_version, worker_type,
        max_capacity, timeout."""

    @abstractmethod
    def get_runs(self, job_name: str, max_results: int = 50) -> list[dict]:
        """Runs for one job, newest first: run_id, status, started_on,
        completed_on, execution_time, error_message, dpu_seconds.
        Raises JobNotFoundError for an unknown job."""

    @abstractmethod
    def record_anomalies(self, db: Session, anomalies: list[dict]) -> None:
        """Persist anomalies found by a scan (or not, if the source derives
        history on read)."""

    @abstractmethod
    def anomaly_history(self, db: Session, limit: int) -> list[dict]:
        """Past anomaly detections, newest first."""

    @abstractmethod
    def health_checks(self) -> dict[str, dict]:
        """Per-dependency status dicts for /health/deep. A status of "skipped"
        means the check does not apply to this source."""
