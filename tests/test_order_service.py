import sys
import json
from pathlib import Path

import pytest

ORDER_SERVICE = Path(__file__).resolve().parents[1] / "order-service"
sys.path.insert(0, str(ORDER_SERVICE))

from app import create_app
from models import db, Order, OutboxEvent


@pytest.fixture
def client(tmp_path):
    database_path = tmp_path / "test_orders.db"

    app = create_app(
        database_url=f"sqlite:///{database_path.as_posix()}"
    )
    app.config["TESTING"] = True

    with app.test_client() as test_client:
        yield test_client


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json["status"] == "healthy"


def test_create_order(client):
    response = client.post(
        "/orders",
        json={
            "customer_id": 101,
            "product_id": 50,
            "quantity": 2,
        },
    )

    assert response.status_code == 201
    assert response.json["status"] == "PLACED"
    assert response.json["order_id"] > 0
    assert response.json["correlation_id"]


def test_invalid_order(client):
    response = client.post(
        "/orders",
        json={
            "customer_id": 101,
            "product_id": 50,
            "quantity": -2,
        },
    )

    assert response.status_code == 400


def test_get_order(client):
    created = client.post(
        "/orders",
        json={
            "customer_id": 102,
            "product_id": 60,
            "quantity": 1,
        },
    )

    order_id = created.json["order_id"]
    response = client.get(f"/orders/{order_id}")

    assert response.status_code == 200
    assert response.json["customer_id"] == 102


def test_order_not_found(client):
    response = client.get("/orders/99999")

    assert response.status_code == 404


def test_outbox_event_created(client):
    response = client.post(
        "/orders",
        json={
            "customer_id": 103,
            "product_id": 70,
            "quantity": 3,
        },
    )

    assert response.status_code == 201

    app = client.application

    with app.app_context():
        event = OutboxEvent.query.first()
        order = Order.query.first()

        assert order is not None
        assert event is not None
        assert event.event_type == "OrderPlaced"
        assert event.published is False

        payload = json.loads(event.payload)

        assert payload["order_id"] == order.id
        assert payload["correlation_id"] == response.json["correlation_id"]