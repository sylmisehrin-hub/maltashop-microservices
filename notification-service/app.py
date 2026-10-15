import os
from flask import Flask, jsonify
from models import db, Notification


def create_app(database_url=None):
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        database_url
        if database_url is not None
        else os.getenv("DATABASE_URL", "sqlite:///notifications.db")
    )

    db.init_app(app)

    with app.app_context():
        db.create_all()

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "healthy"}), 200

    @app.route("/notifications", methods=["GET"])
    def get_notifications():
        notifications = Notification.query.order_by(
            Notification.id.desc()
        ).all()

        return jsonify([
            {
                "id": n.id,
                "order_id": n.order_id,
                "customer_id": n.customer_id,
                "correlation_id": n.correlation_id,
                "message": n.message,
            }
            for n in notifications
        ]), 200

    return app


# Used by Docker and the notification worker.
app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)