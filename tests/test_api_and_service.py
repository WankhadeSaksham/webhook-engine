from unittest.mock import patch
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.connection import SessionLocal
from app.models.webhook import Webhook, WebhookDelivery
from app.services.delivery_service import DeliveryService

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "webhook-engine"


def test_create_webhook_validation_error():
    # Empty message should fail pydantic validation
    response = client.post("/webhooks", json={"message": ""})
    assert response.status_code == 422


@patch("app.services.webhook_service.deliver_webhook_task.delay")
def test_create_webhook_success(mock_celery):
    unique_msg = f"Test event {uuid.uuid4()}"
    response = client.post("/webhooks", json={
        "message": unique_msg,
        "target_url": "http://127.0.0.1:9000/success",
        "event_type": "unit.test"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["status"] == "queued"
    mock_celery.assert_called_once()


@patch("app.services.webhook_service.deliver_webhook_task.delay")
def test_idempotency_deduplication(mock_celery):
    unique_key = f"idem_{uuid.uuid4()}"
    payload = {
        "message": "Payment 100 USD",
        "target_url": "http://127.0.0.1:9000/success",
        "idempotency_key": unique_key
    }
    
    # First dispatch -> 201 Created
    res1 = client.post("/webhooks", json=payload)
    assert res1.status_code == 201
    data1 = res1.json()
    webhook_id_1 = data1["id"]

    # Second dispatch with identical idempotency_key -> 200 OK with same ID
    res2 = client.post("/webhooks", json=payload)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["id"] == webhook_id_1
    assert "idempotency key matched" in data2["message"]

    # Celery should only have been called once!
    assert mock_celery.call_count == 1


def test_get_metrics_endpoint():
    response = client.get("/webhooks/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_webhooks" in data
    assert "delivered" in data
    assert "failed" in data
    assert "total_attempts" in data


@patch("httpx.Client.post")
def test_delivery_service_success_lifecycle(mock_post):
    # Mock receiver 200 OK response
    mock_post.return_value.status_code = 200
    mock_post.return_value.text = '{"status": "received"}'

    db = SessionLocal()
    try:
        # Create a test webhook
        webhook = Webhook(
            message="Test mock success",
            target_url="http://127.0.0.1:9000/success",
            status="queued",
            attempts=0
        )
        db.add(webhook)
        db.commit()
        db.refresh(webhook)

        # Execute delivery attempt 1
        success, error = DeliveryService.execute_delivery(db, webhook.id, current_attempt=1)
        assert success is True
        assert error is None

        # Verify webhook state was updated in DB
        db.refresh(webhook)
        assert webhook.status == "delivered"
        assert webhook.attempts == 1

        # Verify attempt record in webhook_deliveries
        delivery = db.query(WebhookDelivery).filter(WebhookDelivery.webhook_id == webhook.id).first()
        assert delivery is not None
        assert delivery.attempt_number == 1
        assert delivery.status == "delivered"
        assert delivery.response_status_code == 200
        assert delivery.duration_ms is not None
    finally:
        db.close()


@patch("httpx.Client.post")
def test_delivery_service_retry_and_failure_lifecycle(mock_post):
    # Mock receiver 500 error response
    mock_post.return_value.status_code = 500
    mock_post.return_value.text = '{"error": "Internal Error"}'

    db = SessionLocal()
    try:
        webhook = Webhook(
            message="Test mock fail",
            target_url="http://127.0.0.1:9000/fail",
            status="queued",
            attempts=0
        )
        db.add(webhook)
        db.commit()
        db.refresh(webhook)

        # Attempt 1: Should enter 'retrying'
        success1, error1 = DeliveryService.execute_delivery(db, webhook.id, current_attempt=1)
        assert success1 is False
        db.refresh(webhook)
        assert webhook.status == "retrying"

        # Attempt 2: Should still be 'retrying'
        success2, error2 = DeliveryService.execute_delivery(db, webhook.id, current_attempt=2)
        assert success2 is False
        db.refresh(webhook)
        assert webhook.status == "retrying"

        # Attempt 3: Final attempt (MAX_RETRIES=3) -> must mark 'failed'
        success3, error3 = DeliveryService.execute_delivery(db, webhook.id, current_attempt=3)
        assert success3 is False
        db.refresh(webhook)
        assert webhook.status == "failed"

        # Verify 3 attempt records were logged
        deliveries = db.query(WebhookDelivery).filter(WebhookDelivery.webhook_id == webhook.id).all()
        assert len(deliveries) == 3
        assert all(d.status == "failed" for d in deliveries)
        assert all(d.response_status_code == 500 for d in deliveries)
    finally:
        db.close()
