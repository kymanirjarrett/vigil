# Vigil AWS Infrastructure

CloudFormation template that provisions all AWS resources for the Vigil ETL monitoring platform.

## What the stack provisions

| Resource | Name pattern | Purpose |
|---|---|---|
| S3 | `vigil-pipeline-input-<account>-<env>` | Raw sales CSV input |
| S3 | `vigil-pipeline-output-<account>-<env>` | Processed Parquet output |
| S3 | `vigil-athena-results-<account>-<env>` | Athena query result output location |
| S3 | `vigil-glue-scripts-<account>-<env>` | Glue job Python scripts |
| IAM Role | `vigil-glue-role-<env>` | Glue service role |
| IAM User | `vigil-backend-<env>` | Backend app user (read-only) |
| IAM Policy | `vigil-backend-readonly-<env>` | Grants Glue/CW/S3/Athena read access |
| Glue Database | `vigil_analytics_<env>` | Catalog database |
| Glue Table | `vigil_sales_daily` | Daily aggregated sales (Parquet) |
| Glue Job | `vigil-sales-aggregation-<env>` | Python Shell ETL job |
| Glue Crawler | `vigil-sales-crawler-<env>` | Updates table stats after ETL run |

## Deploy via GitHub Actions (recommended)

Go to **Actions → Deploy CloudFormation Stack → Run workflow**, then select:
- **environment**: `nonprod` or `prod`
- **action**: `deploy` or `delete`

`prod` deployments require a manual approval from a repository admin (configured under Settings → Environments → prod → Required reviewers).

## Deploy via CLI (one-command alternative)

```bash
aws cloudformation deploy \
  --template-file infra/vigil-stack.yaml \
  --stack-name vigil-nonprod \
  --parameter-overrides Environment=nonprod \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-2

# Upload Glue script and seed data
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
aws s3 cp infra/glue-scripts/sales_aggregation.py \
  s3://vigil-glue-scripts-${ACCOUNT}-nonprod/sales_aggregation.py
aws s3 cp infra/seed-data/sales_data.csv \
  s3://vigil-pipeline-input-${ACCOUNT}-nonprod/sales_data.csv
```

## After deploying

1. **Create IAM access keys** for `vigil-backend-nonprod` in the AWS console (IAM → Users → Security credentials). These become `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` in the backend `.env`.

2. **Configure Athena output location** — in the Athena console, set the workgroup query result location to `s3://vigil-athena-results-<account>-nonprod/`.

3. **Run the ETL job** — in the Glue console, trigger `vigil-sales-aggregation-nonprod` once to populate the output bucket with Parquet data.

4. **Run the crawler** (optional) — `vigil-sales-crawler-nonprod` updates table statistics so Athena query plans are accurate.

5. **Set backend env vars**:
   ```
   GLUE_DATABASE_NAME=vigil_analytics_nonprod
   GLUE_TABLE_NAME=vigil_sales_daily
   ATHENA_RESULTS_BUCKET=vigil-athena-results-<account>-nonprod
   ```

## Tear down

```bash
aws cloudformation delete-stack --stack-name vigil-nonprod --region us-east-2
```

Or use the GitHub Actions workflow with `action: delete`.

> **Note:** S3 buckets must be empty before CloudFormation can delete them. Empty them manually first, or the delete will fail with a `BucketNotEmpty` error.

## Cost

A single demo run of `vigil-sales-aggregation` (Python Shell, 0.0625 DPU, ~30 seconds) costs roughly **< $0.01**. Idle stack resources (empty S3 buckets, IAM, Glue catalog) have no ongoing compute cost.
