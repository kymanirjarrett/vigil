"""
Vigil — Sales Aggregation Glue Job (Python Shell)
Reads raw sales CSV from S3, deduplicates, aggregates by day, writes Parquet.
"""
import argparse
import io
import sys
from datetime import datetime, timezone

import boto3
import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--JOB_NAME", type=str, default="vigil-sales-aggregation")
    parser.add_argument("--INPUT_BUCKET", type=str, required=True)
    parser.add_argument("--OUTPUT_BUCKET", type=str, required=True)
    args, _ = parser.parse_known_args()
    return args


def main():
    args = parse_args()
    s3 = boto3.client("s3")

    print(f"Reading s3://{args.INPUT_BUCKET}/sales_data.csv")
    obj = s3.get_object(Bucket=args.INPUT_BUCKET, Key="sales_data.csv")
    df = pd.read_csv(io.BytesIO(obj["Body"].read()))
    print(f"Loaded {len(df)} raw rows")

    df = df.drop_duplicates(subset=["order_id"])

    daily = (
        df.groupby("date")
        .agg(
            total_revenue=("revenue", "sum"),
            total_quantity=("quantity", "sum"),
            avg_order_value=("revenue", "mean"),
            transaction_count=("order_id", "count"),
        )
        .reset_index()
        .sort_values("date")
    )
    daily["avg_order_value"] = daily["avg_order_value"].round(2)
    print(f"Aggregated into {len(daily)} daily summaries")

    buf = io.BytesIO()
    daily.to_parquet(buf, index=False, engine="pyarrow")
    buf.seek(0)

    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    key = f"daily/sales_daily_{ts}.parquet"
    s3.put_object(Bucket=args.OUTPUT_BUCKET, Key=key, Body=buf.getvalue())
    print(f"Wrote s3://{args.OUTPUT_BUCKET}/{key}")


if __name__ == "__main__":
    main()
