"""Server-side settings read once from the environment."""
import os

from dotenv import load_dotenv

load_dotenv()

VALID_DATA_SOURCES = ("seed", "aws")

# Where pipeline data (jobs, runs, anomalies) comes from.
#   seed: deterministic sample data, no AWS calls, no email (the default)
#   aws:  live AWS Glue via boto3, real SendGrid email
DATA_SOURCE = os.getenv("DATA_SOURCE", "seed").strip().lower()

if DATA_SOURCE not in VALID_DATA_SOURCES:
    raise RuntimeError(
        f"DATA_SOURCE must be one of {VALID_DATA_SOURCES}, got {DATA_SOURCE!r}"
    )
