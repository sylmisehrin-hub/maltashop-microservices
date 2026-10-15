import json
import os
import pika


def publish_event(event):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=os.getenv("RABBITMQ_HOST", "localhost"),
            port=int(os.getenv("RABBITMQ_PORT", "5672")),
            heartbeat=30,
            blocked_connection_timeout=10
        )
    )

    try:
        channel = connection.channel()

        channel.queue_declare(
            queue="order_events",
            durable=True
        )

        channel.confirm_delivery()

        channel.basic_publish(
            exchange="",
            routing_key="order_events",
            body=json.dumps(event),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
                correlation_id=event["correlation_id"]
            ),
            mandatory=True
        )

        print(
            f"Published OrderPlaced event: "
            f"{event['correlation_id']}"
        )
    finally:
        connection.close()