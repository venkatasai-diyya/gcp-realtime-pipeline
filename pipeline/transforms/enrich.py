"""Enrich parsed events with metadata before writing to BigQuery."""

import json
import logging
from datetime import datetime, timezone

import apache_beam as beam

logger = logging.getLogger(__name__)


class EnrichEventFn(beam.DoFn):
    """
    Adds pipeline metadata fields required by the BigQuery schema:
      - processed_at  : UTC timestamp of enrichment
      - ingest_date   : DATE partition key (YYYY-MM-DD)
      - pipeline_version
      - payload       : remaining fields serialised to JSON
    """

    def __init__(self, pipeline_version: str = "1.0.0"):
        self.pipeline_version = pipeline_version

    def process(self, element, *args, **kwargs):
        now = datetime.now(tz=timezone.utc)

        core_fields = {"event_id", "event_type", "user_id"}
        payload = {k: v for k, v in element.items() if k not in core_fields}

        enriched = {
            "event_id":        element["event_id"],
            "event_type":      element["event_type"],
            "user_id":         element.get("user_id"),
            "payload":         json.dumps(payload),
            "processed_at":    now.isoformat(),
            "ingest_date":     now.date().isoformat(),
            "pipeline_version": self.pipeline_version,
        }

        yield enriched
