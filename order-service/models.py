from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(30), default="PLACED")
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )


class OutboxEvent(db.Model):
    __tablename__ = "outbox_events"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(36), unique=True, nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    payload = db.Column(db.Text, nullable=False)
    published = db.Column(db.Boolean, default=False, nullable=False)