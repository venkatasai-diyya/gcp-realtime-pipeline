"""Parse raw Pub/Sub messages into structured dicts."""

import json
import logging
import apache_beam as beam

logger = logging.getLogger(__name__)


class ParseEventFn(beam.DoFn):
    """
    Deserialise raw Pub/Sub message bytes.
    Emits valid events to main output; bad messages to 'dead_letter'.
    """

    DEAD_LETTER = "dead_letter"

    def process(self, message, *args, **kwargs):
        try:
            data = json.loads(message.data.decode("utf-8"))

            if "event_id" not in data or "event_type" not in data:
                raise ValueError(f"Missing required fields in: {data}")

            yield data

        except Exception as exc:
            logger.warning("ParseEventFn failed: %s | raw=%s", exc, message.data)
            yield beam.pvalue.TaggedOutput(
                self.DEAD_LETTER,
                {
                    "raw": message.data.decode("utf-8", errors="replace"),
                    "error": str(exc),
                    "publish_time": str(message.publish_time),
                },
            )
