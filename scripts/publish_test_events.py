"""
scripts/publish_test_events.py
Publishes synthetic events to Pub/Sub for local/dev pipeline testing.

Usage:
    python scripts/publish_test_events.py \
        --project YOUR_PROJECT_ID \
        --topic events-topic \
        --count 100 \
        --interval 0.1
"""

import argparse
import json
import random
import time
import uuid
from datetime import datetime, timezone

from google.cloud import pubsub_v1

EVENT_TYPES = ["page_view", "click", "purchase", "session_start", "session_end", "error"]
PAGES = ["/home", "/products", "/cart", "/checkout", "/account"]


def make_event(event_type: str | None = None) -> dict:
    etype = event_type or random.choice(EVENT_TYPES)
    event = {
        "event_id":   str(uuid.uuid4()),
        "event_type": etype,
        "user_id":    f"user_{random.randint(1000, 9999)}",
        "timestamp":  datetime.now(tz=timezone.utc).isoformat(),
    }

    if etype == "page_view":
        event["page"] = random.choice(PAGES)
        event["referrer"] = "https://google.com"
    elif etype == "purchase":
        event["amount_usd"] = round(random.uniform(10, 500), 2)
        event["product_id"] = f"prod_{random.randint(100, 999)}"
    elif etype == "error":
        event["error_code"] = random.choice(["404", "500", "403"])

    return event


def publish_events(project: str, topic: str, count: int, interval: float):
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project, topic)
    futures = []

    print(f"Publishing {count} events to {topic_path} …")

    for i in range(count):
        event = make_event()
        data = json.dumps(event).encode("utf-8")
        future = publisher.publish(topic_path, data, event_type=event["event_type"])
        futures.append(future)

        if (i + 1) % 10 == 0:
            print(f"  Published {i + 1}/{count} events")

        time.sleep(interval)

    for f in futures:
        f.result()

    print(f"Done. {count} events published.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project",  required=True)
    parser.add_argument("--topic",    default="events-topic")
    parser.add_argument("--count",    default=100, type=int)
    parser.add_argument("--interval", default=0.1, type=float)
    args = parser.parse_args()

    publish_events(args.project, args.topic, args.count, args.interval)
