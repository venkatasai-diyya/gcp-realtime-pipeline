"""Schema validation for parsed events."""

import logging
import apache_beam as beam

logger = logging.getLogger(__name__)

VALID_EVENT_TYPES = {
    "page_view",
    "click",
    "purchase",
    "session_start",
    "session_end",
    "error",
}


class ValidateEventFn(beam.DoFn):
    """
    Validates event fields and filters out records that don't meet schema.
    Invalid events are dropped with a warning (extend to dead-letter if needed).
    """

    def process(self, element, *args, **kwargs):
        event_type = element.get("event_type", "")

        if event_type not in VALID_EVENT_TYPES:
            logger.warning(
                "Unknown event_type '%s' for event_id=%s — dropping.",
                event_type,
                element.get("event_id"),
            )
            return

        if not element.get("event_id"):
            logger.warning("Empty event_id — dropping: %s", element)
            return

        yield element
