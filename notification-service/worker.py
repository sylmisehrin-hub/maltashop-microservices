import json
import os
import pika

from sqlalchemy.exc import IntegrityError
from app import app
from models import db, Notification


def process_event(event):
    with app.app_context():
        notification = Notification(
            event_id=event["event_id"],
            order_id=event["order_id"],
            customer_id=event["customer_id"],
            correlation_id=event["correlation_id"],
            message=f"Order {event['order_id']} placed successfully"
        )

        try:
            db.session.add(notification)
            db.session.commit()

            print(json.dumps({
                "service": "notification-service",
                "event": "OrderPlacedConsumed",
                "order_id": event["order_id"],
                "correlation_id": event["correlation_id"]
            }), flush=True)

        except IntegrityError:
            db.session.rollback()
            print(
                f"Duplicate event ignored: {event['event_id']}",
                flush=True
            )


def callback(ch, method, properties, body):
    try:
        event = json.loads(body)
        process_event(event)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as exc:
        print(f"Event processing failed: {exc}", flush=True)
        ch.basic_nack(
            delivery_tag=method.delivery_tag,
            requeue=False
        )


def start_worker():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=os.getenv("RABBITMQ_HOST", "localhost"),
            port=int(os.getenv("RABBITMQ_PORT", "5672"))
        )
    )

    channel = connection.channel()

    channel.queue_declare(
        queue="order_events",
        durable=True
    )

    channel.basic_qos(prefetch_count=1)

    channel.basic_consume(
        queue="order_events",
        on_message_callback=callback
    )

    print("Notification worker waiting for events...", flush=True)

    try:
        channel.start_consuming()
    finally:
        connection.close()


if __name__ == "__main__":
    start_worker()