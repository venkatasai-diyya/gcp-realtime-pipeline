# Real-Time GCP Streaming Pipeline

**Pub/Sub → Dataflow (Apache Beam) → BigQuery**  
A production-grade streaming data pipeline built on Google Cloud Platform, processing live events with sub-minute latency into a partitioned, clustered BigQuery table ready for analytics and dashboarding.

---

## Architecture

```
Event Sources          Ingestion            Transform                  Storage          Orchestration
(IoT / API / App) ──► Pub/Sub Topic ──► Dataflow (Apache Beam) ──► BigQuery ◄── Cloud Composer
                            │               parse · validate             │         (Airflow DAG)
                            │               enrich · window              │
                            └──► Dead-letter topic                  Looker Studio
                                 (failed msgs)                      (dashboard)
```

Data flows through fixed 60-second tumbling windows. Invalid messages are routed to a dead-letter topic for inspection instead of silently dropped.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Ingestion | Google Cloud Pub/Sub |
| Processing | Apache Beam 2.55 on Google Dataflow |
| Storage | BigQuery (DAY partitioned, clustered by `event_type`, `user_id`) |
| Orchestration | Cloud Composer 2 (Airflow) |
| Infrastructure | Terraform |
| Dashboarding | Looker Studio |
| CI | GitHub Actions |
| Language | Python 3.11 |

---

## Repository Structure

```
gcp-realtime-pipeline/
├── pipeline/
│   ├── main.py                    # Beam pipeline entry point
│   └── transforms/
│       ├── parse.py               # Deserialise Pub/Sub messages
│       ├── validate.py            # Schema + field validation
│       ├── enrich.py              # Add metadata fields
│       └── window.py              # Fixed-time windowing
├── pipeline/tests/
│   └── test_transforms.py         # Unit tests (pytest + Beam TestPipeline)
├── dags/
│   └── pipeline_dag.py            # Airflow DAG — launch + monitor Dataflow job
├── infra/terraform/
│   ├── main.tf                    # Pub/Sub, BigQuery, GCS, IAM
│   └── variables.tf
├── config/
│   └── bq_schema.json             # BigQuery table schema
├── dashboard/
│   └── queries.sql                # Analytics SQL for Looker Studio
├── scripts/
│   └── publish_test_events.py     # Local test event publisher
└── .github/workflows/ci.yml       # GitHub Actions CI
```

---

## Quickstart

### Prerequisites

- GCP project with billing enabled
- `gcloud` CLI authenticated
- Terraform ≥ 1.5
- Python 3.11

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/gcp-realtime-pipeline.git
cd gcp-realtime-pipeline
pip install -r requirements.txt
```

### 2. Provision GCP infrastructure

```bash
cd infra/terraform

terraform init
terraform plan -var="project_id=YOUR_PROJECT_ID"
terraform apply -var="project_id=YOUR_PROJECT_ID"
```

This creates: Pub/Sub topic + subscription + dead-letter topic, BigQuery dataset + partitioned table, GCS buckets for Dataflow temp and Flex Templates, a dedicated Dataflow service account with least-privilege IAM.

### 3. Run unit tests

```bash
pytest pipeline/tests/ -v --cov=pipeline
```

### 4. Publish test events (dev/local)

```bash
python scripts/publish_test_events.py \
  --project YOUR_PROJECT_ID \
  --topic events-topic \
  --count 500 \
  --interval 0.05
```

### 5. Launch the Dataflow pipeline

**Direct runner (local dev):**

```bash
python -m pipeline.main \
  --project YOUR_PROJECT_ID \
  --subscription projects/YOUR_PROJECT_ID/subscriptions/events-sub \
  --bq_dataset events_streaming \
  --bq_table events_raw \
  --runner DirectRunner
```

**Dataflow runner (GCP):**

```bash
python -m pipeline.main \
  --project YOUR_PROJECT_ID \
  --subscription projects/YOUR_PROJECT_ID/subscriptions/events-sub \
  --bq_dataset events_streaming \
  --bq_table events_raw \
  --runner DataflowRunner \
  --region us-central1 \
  --temp_location gs://YOUR_PROJECT_ID-df-temp/temp \
  --pipeline_version 1.0.0
```

### 6. Monitor in BigQuery

```sql
SELECT event_type, COUNT(*) as events
FROM `YOUR_PROJECT_ID.events_streaming.events_raw`
WHERE ingest_date = CURRENT_DATE()
GROUP BY 1
ORDER BY 2 DESC;
```

---

## Event Schema

Published Pub/Sub messages must be JSON with at minimum:

```json
{
  "event_id": "uuid-string",
  "event_type": "page_view | click | purchase | session_start | session_end | error",
  "user_id": "optional-string",
  "...": "any additional fields go into the payload JSON column"
}
```

---

## BigQuery Table Design

| Column | Type | Notes |
|---|---|---|
| `event_id` | STRING | Primary deduplication key |
| `event_type` | STRING | Clustering column |
| `user_id` | STRING | Clustering column — nullable for anon sessions |
| `payload` | JSON | All additional event-specific fields |
| `processed_at` | TIMESTAMP | UTC processing time |
| `ingest_date` | DATE | Partition key — prune queries by date |
| `pipeline_version` | STRING | Lineage tracking |

Partitioning by `ingest_date` + clustering by `(event_type, user_id)` reduces query costs by up to 80% for typical analytics patterns.

---

## Orchestration

The Airflow DAG (`dags/pipeline_dag.py`) runs daily and:

1. Launches the Dataflow Flex Template job
2. Waits for the BigQuery partition to appear
3. Runs a data quality check (non-zero row count, no null event IDs)

Deploy it to Cloud Composer by uploading `pipeline_dag.py` to your Composer environment's DAGs GCS bucket.

---

## Extending the Pipeline

- **Add a new event type** — update `VALID_EVENT_TYPES` in `validate.py` and the BigQuery schema if new columns are needed.
- **Change windowing strategy** — modify `apply_windowing()` in `transforms/window.py` (e.g. sliding windows, session windows).
- **Add a dead-letter consumer** — create a second Beam pipeline reading from `events-dead-letter` and writing failed events to a separate BQ table for inspection.
- **Add schema evolution** — use `BigQueryDisposition.WRITE_APPEND` with `additional_bq_parameters` to allow new columns without breaking existing data.

---

## CI/CD

GitHub Actions runs on every push:

- **Test** — `pytest` with 80% coverage threshold
- **Lint** — `ruff` code quality checks

See `.github/workflows/ci.yml`.

---

## License

MIT
