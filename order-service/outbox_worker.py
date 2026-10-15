import json
import time
import logging

from app import app
from models import db, OutboxEvent
from publisher import publish_event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("outbox-worker")


def process_outbox():
    with app.app_context():
        events = OutboxEvent.query.filter_by(
            published=False
        ).order_by(OutboxEvent.id).limit(20).all()

        for event in events:
            try:
                payload = json.loads(event.payload)

                publish_event(payload)

                event.published = True
                db.session.commit()

                logger.info(
                    "Published outbox event %s",
                    event.event_id
                )

            except Exception:
                db.session.rollback()
                logger.exception(
                    "Failed to publish event %s",
                    event.event_id
                )


if __name__ == "__main__":
    logger.info("Outbox worker started")

    while True:
        process_outbox()
        time.sleep(5)