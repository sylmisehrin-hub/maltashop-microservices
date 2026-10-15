import sys
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SERVICE_DIR = ROOT / "notification-service"


@pytest.fixture
def notification_app(tmp_path):
    original_path = list(sys.path)
    original_modules = {
        name: sys.modules.get(name)
        for name in ("app", "models")
    }

    try:
        sys.modules.pop("app", None)
        sys.modules.pop("models", None)
        sys.path.insert(0, str(SERVICE_DIR))

        spec = importlib.util.spec_from_file_location(
            "app", SERVICE_DIR / "app.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules["app"] = module
        spec.loader.exec_module(module)

        database_path = tmp_path / "test_notifications.db"

        app = module.create_app(
            database_url=f"sqlite:///{database_path.as_posix()}"
        )
        app.config["TESTING"] = True

        yield app, module.db, module.Notification

    finally:
        sys.path[:] = original_path

        for name, original in original_modules.items():
            sys.modules.pop(name, None)
            if original is not None:
                sys.modules[name] = original


def test_notification_health(notification_app):
    app, _, _ = notification_app

    with app.test_client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json["status"] == "healthy"


def test_empty_notifications(notification_app):
    app, _, _ = notification_app

    with app.test_client() as client:
        response = client.get("/notifications")

    assert response.status_code == 200
    assert response.json == []


def test_notification_retrieval(notification_app):
    app, db, Notification = notification_app

    with app.app_context():
        notification = Notification(
            event_id="test-event-001",
            order_id=10,
            customer_id=101,
            correlation_id="test-correlation-001",
            message="Order 10 placed successfully",
        )

        db.session.add(notification)
        db.session.commit()

    with app.test_client() as client:
        response = client.get("/notifications")

    assert response.status_code == 200
    assert len(response.json) == 1
    assert response.json[0]["order_id"] == 10
    assert response.json[0]["customer_id"] == 101
    assert response.json[0]["message"] == "Order 10 placed successfully"


def test_notification_ordering(notification_app):
    app, db, Notification = notification_app

    with app.app_context():
        for i in range(1, 4):
            db.session.add(
                Notification(
                    event_id=f"test-event-{i}",
                    order_id=i,
                    customer_id=100 + i,
                    correlation_id=f"correlation-{i}",
                    message=f"Order {i} placed successfully",
                )
            )

        db.session.commit()

    with app.test_client() as client:
        response = client.get("/notifications")

    assert response.status_code == 200

    order_ids = [
        item["order_id"]
        for item in response.json
    ]

    assert order_ids == [3, 2, 1]