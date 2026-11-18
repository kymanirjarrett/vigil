"""Pick the pipeline data source once, from the DATA_SOURCE setting.

Routers take the provider as a FastAPI dependency:

    provider: DataProvider = Depends(get_data_provider)

so they never branch on the source themselves, and tests can swap it with
app.dependency_overrides.
"""
from functools import lru_cache

import settings
from data_sources.base import DataProvider, DataSourceError, JobNotFoundError

__all__ = ["DataProvider", "DataSourceError", "JobNotFoundError", "get_data_provider"]


@lru_cache(maxsize=1)
def get_data_provider() -> DataProvider:
    if settings.DATA_SOURCE == "aws":
        # Imported here so boto3 is never loaded in seed mode.
        from data_sources.aws import AwsDataProvider
        return AwsDataProvider()
    from data_sources.seed import SeedDataProvider
    return SeedDataProvider()
