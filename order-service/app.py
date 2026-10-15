import os
import json
import uuid

from flask import Flask, request, jsonify
from models import db, Order, OutboxEvent


def create_app(database_url=None):
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        database_url
        if database_url is not None
        else os.getenv("DATABASE_URL", "sqlite:///orders.db")
    )

    db.init_app(app)

    with app.app_context():
        db.create_all()

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "healthy"}), 200

    @app.route("/orders", methods=["POST"])
    def create_order():
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({"error": "Valid JSON object required"}), 400

        customer_id = data.get("customer_id")
        product_id = data.get("product_id")
        quantity = data.get("quantity")

        values = [customer_id, product_id, quantity]

        if any(
            not isinstance(value, int) or isinstance(value, bool)
            for value in values
        ):
            return jsonify({"error": "All fields must be integers"}), 400

        if any(value <= 0 for value in values):
            return jsonify({"error": "All values must be positive"}), 400

        correlation_id = str(uuid.uuid4())
        event_id = str(uuid.uuid4())

        try:
            order = Order(
                customer_id=customer_id,
                product_id=product_id,
                quantity=quantity,
            )

            db.session.add(order)
            db.session.flush()

            event = {
                "event_id": event_id,
                "event_type": "OrderPlaced",
                "order_id": order.id,
                "customer_id": customer_id,
                "product_id": product_id,
                "quantity": quantity,
                "correlation_id": correlation_id,
            }

            outbox = OutboxEvent(
                event_id=event_id,
                event_type="OrderPlaced",
                payload=json.dumps(event),
                published=False,
            )

            db.session.add(outbox)
            db.session.commit()

        except Exception:
            db.session.rollback()
            app.logger.exception("Order creation failed")
            return jsonify({"error": "Unable to create order"}), 500

        return jsonify({
            "order_id": order.id,
            "status": order.status,
            "correlation_id": correlation_id,
            "message": "Order created successfully",
        }), 201

    @app.route("/orders/<int:order_id>", methods=["GET"])
    def get_order(order_id):
        order = db.session.get(Order, order_id)

        if not order:
            return jsonify({"error": "Order not found"}), 404

        return jsonify({
            "order_id": order.id,
            "customer_id": order.customer_id,
            "product_id": order.product_id,
            "quantity": order.quantity,
            "status": order.status,
        }), 200

    return app



app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)