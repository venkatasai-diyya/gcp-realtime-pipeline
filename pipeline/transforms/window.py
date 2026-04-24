"""Windowing strategies for the streaming pipeline."""

import apache_beam as beam
from apache_beam.transforms.window import FixedWindows


def apply_windowing(pcollection, window_size_secs: int = 60):
    """
    Apply fixed-time windows to the stream.
    Default: 60-second tumbling windows.
    Extend here to add sliding or session windows per event_type.
    """
    return (
        pcollection
        | "ApplyFixedWindow" >> beam.WindowInto(
            FixedWindows(window_size_secs)
        )
    )
