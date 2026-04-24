"""Unit tests for pipeline transforms."""

import unittest
import apache_beam as beam
from apache_beam.testing.test_pipeline import TestPipeline
from apache_beam.testing.util import assert_that, equal_to

from pipeline.transforms.validate import ValidateEventFn
from pipeline.transforms.enrich import EnrichEventFn


class TestValidateEventFn(unittest.TestCase):

    def test_valid_event_passes_through(self):
        valid = {"event_id": "abc-123", "event_type": "page_view", "user_id": "u1"}
        with TestPipeline() as p:
            result = (
                p
                | beam.Create([valid])
                | beam.ParDo(ValidateEventFn())
            )
            assert_that(result, equal_to([valid]))

    def test_unknown_event_type_filtered(self):
        bad = {"event_id": "xyz-999", "event_type": "unknown_type"}
        with TestPipeline() as p:
            result = (
                p
                | beam.Create([bad])
                | beam.ParDo(ValidateEventFn())
            )
            assert_that(result, equal_to([]))

    def test_missing_event_id_filtered(self):
        bad = {"event_id": "", "event_type": "click"}
        with TestPipeline() as p:
            result = (
                p
                | beam.Create([bad])
                | beam.ParDo(ValidateEventFn())
            )
            assert_that(result, equal_to([]))


class TestEnrichEventFn(unittest.TestCase):

    def test_enrichment_adds_required_fields(self):
        event = {"event_id": "e1", "event_type": "click", "user_id": "u1"}
        with TestPipeline() as p:
            result = (
                p
                | beam.Create([event])
                | beam.ParDo(EnrichEventFn(pipeline_version="test-1.0"))
            )

            def check(elements):
                self.assertEqual(len(elements), 1)
                row = elements[0]
                self.assertIn("processed_at", row)
                self.assertIn("ingest_date", row)
                self.assertEqual(row["pipeline_version"], "test-1.0")
                self.assertEqual(row["event_id"], "e1")

            assert_that(result, check)


if __name__ == "__main__":
    unittest.main()
