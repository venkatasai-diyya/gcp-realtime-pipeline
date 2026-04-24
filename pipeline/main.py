"""
Real-Time GCP Streaming Pipeline
Pub/Sub → Dataflow (Apache Beam) → BigQuery
"""

import json
import logging
import argparse
from datetime import datetime

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions
from apache_beam.io.gcp.pubsub import ReadFromPubSub
from apache_beam.io.gcp.bigquery import WriteToBigQuery, BigQueryDisposition

from pipeline.transforms.parse import ParseEventFn
from pipeline.transforms.enrich import EnrichEventFn
from pipeline.transforms.validate import ValidateEventFn
from pipeline.transforms.window import apply_windowing

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_bq_schema():
    return {
        "fields": [
            {"name": "event_id",       "type": "STRING",    "mode": "REQUIRED"},
            {"name": "event_type",     "type": "STRING",    "mode": "REQUIRED"},
            {"name": "user_id",        "type": "STRING",    "mode": "NULLABLE"},
            {"name": "payload",        "type": "JSON",      "mode": "NULLABLE"},
            {"name": "processed_at",   "type": "TIMESTAMP", "mode": "REQUIRED"},
            {"name": "ingest_date",    "type": "DATE",      "mode": "REQUIRED"},
            {"name": "pipeline_version","type": "STRING",   "mode": "REQUIRED"},
        ]
    }


def run(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--project",          required=True)
    parser.add_argument("--subscription",     required=True, help="Pub/Sub subscription path")
    parser.add_argument("--bq_dataset",       required=True)
    parser.add_argument("--bq_table",         required=True)
    parser.add_argument("--window_size_secs", default=60,  type=int)
    parser.add_argument("--pipeline_version", default="1.0.0")
    known_args, pipeline_args = parser.parse_known_args(argv)

    options = PipelineOptions(pipeline_args)
    options.view_as(StandardOptions).streaming = True

    table_ref = f"{known_args.project}:{known_args.bq_dataset}.{known_args.bq_table}"

    with beam.Pipeline(options=options) as p:
        raw_events = (
            p
            | "ReadFromPubSub" >> ReadFromPubSub(
                subscription=known_args.subscription,
                with_attributes=True,
            )
        )

        parsed = (
            raw_events
            | "ParseEvents"    >> beam.ParDo(ParseEventFn())
            | "ValidateEvents" >> beam.ParDo(ValidateEventFn())
            | "EnrichEvents"   >> beam.ParDo(
                EnrichEventFn(
                    pipeline_version=known_args.pipeline_version
                )
            )
        )

        windowed = apply_windowing(parsed, known_args.window_size_secs)

        _ = (
            windowed
            | "WriteToBigQuery" >> WriteToBigQuery(
                table=table_ref,
                schema=get_bq_schema(),
                write_disposition=BigQueryDisposition.WRITE_APPEND,
                create_disposition=BigQueryDisposition.CREATE_IF_NEEDED,
                additional_bq_parameters={
                    "timePartitioning": {
                        "type": "DAY",
                        "field": "ingest_date",
                    },
                    "clustering": {"fields": ["event_type", "user_id"]},
                },
            )
        )

    logger.info("Pipeline started successfully.")


if __name__ == "__main__":
    run()
