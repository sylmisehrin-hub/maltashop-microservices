from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(36), unique=True, nullable=False)
    order_id = db.Column(db.Integer, nullable=False)
    customer_id = db.Column(db.Integer, nullable=False)
    correlation_id = db.Column(db.String(36), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )