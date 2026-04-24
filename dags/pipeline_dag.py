"""
Cloud Composer (Airflow) DAG
Schedules and monitors the Dataflow streaming pipeline job.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.google.cloud.operators.dataflow import DataflowStartFlexTemplateOperator
from airflow.providers.google.cloud.sensors.bigquery import BigQueryTablePartitionExistenceSensor
from airflow.providers.google.cloud.operators.bigquery import BigQueryCheckOperator

PROJECT_ID   = "ai-ml-labs"
REGION       = "us-central1"
DATASET      = "events_streaming"
TABLE        = "events_raw"
SUBSCRIPTION = "projects/ai-ml-labs/subscriptions/events-sub"
TEMPLATE_PATH = "gs://ai-ml-labs-templates/realtime-pipeline"

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": True,
    "email": ["venkatasaidiyya@gmail.com"],
}

with DAG(
    dag_id="gcp_realtime_pipeline",
    description="Launch and monitor the Pub/Sub → Dataflow → BigQuery streaming pipeline",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval="0 6 * * *",  # Daily at 6 AM UTC
    catchup=False,
    tags=["streaming", "dataflow", "bigquery"],
) as dag:

    launch_pipeline = DataflowStartFlexTemplateOperator(
        task_id="launch_dataflow_pipeline",
        project_id=PROJECT_ID,
        location=REGION,
        body={
            "launchParameter": {
                "jobName": "realtime-events-pipeline-{{ ds_nodash }}",
                "containerSpecGcsPath": TEMPLATE_PATH,
                "parameters": {
                    "project":          PROJECT_ID,
                    "subscription":     SUBSCRIPTION,
                    "bq_dataset":       DATASET,
                    "bq_table":         TABLE,
                    "window_size_secs": "60",
                    "pipeline_version": "1.0.0",
                },
            }
        },
    )

    wait_for_partition = BigQueryTablePartitionExistenceSensor(
        task_id="wait_for_bq_partition",
        project_id=PROJECT_ID,
        dataset_id=DATASET,
        table_id=TABLE,
        partition_id="{{ ds_nodash }}",
        timeout=3600,
        poke_interval=120,
    )

    data_quality_check = BigQueryCheckOperator(
        task_id="data_quality_check",
        sql=f"""
            SELECT COUNT(*) > 0
            FROM `ai-ml-labs.events_streaming.events_raw`
            WHERE ingest_date = '{{{{ ds }}}}'
              AND event_id IS NOT NULL
              AND event_type IS NOT NULL
        """,
        use_legacy_sql=False,
        gcp_conn_id="google_cloud_default",
    )

    launch_pipeline >> wait_for_partition >> data_quality_check