from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.webhook import (
    WebhookCreate,
    WebhookCreateResponse,
    WebhookResponse,
    WebhookDetailResponse
)
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("", response_model=WebhookCreateResponse, status_code=status.HTTP_201_CREATED)
def create_webhook(
    webhook_in: WebhookCreate,
    response: Response,
    db: Session = Depends(get_db)
):
    """Accepts and queues an outgoing webhook event asynchronously.
    
    Returns 201 Created for a new webhook event.
    Returns 200 OK if the idempotency_key was already received (deduplication).
    """
    webhook, is_duplicate = WebhookService.create_and_enqueue_webhook(db, webhook_in)
    
    if is_duplicate:
        response.status_code = status.HTTP_200_OK
        return WebhookCreateResponse(
            id=webhook.id,
            status=webhook.status,
            message="Existing webhook returned (idempotency key matched).",
            idempotency_key=webhook.idempotency_key,
            target_url=webhook.target_url
        )

    return WebhookCreateResponse(
        id=webhook.id,
        status=webhook.status,
        message="Webhook accepted and queued for delivery.",
        idempotency_key=webhook.idempotency_key,
        target_url=webhook.target_url
    )


@router.get("", response_model=List[WebhookResponse])
def list_webhooks(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (pending, queued, delivered, failed)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Lists webhooks with optional status filtering and pagination."""
    webhooks, _ = WebhookService.list_webhooks(db, status=status_filter, limit=limit, offset=offset)
    return webhooks


@router.get("/metrics", response_model=dict)
def get_metrics(db: Session = Depends(get_db)):
    """Returns aggregated delivery statistics, status counts, and success rates."""
    return WebhookService.get_metrics(db)


@router.get("/predict-failure", response_model=dict)
def predict_webhook_failure(
    target_url: str = Query(..., description="Destination webhook URL to analyze"),
    attempt: int = Query(1, ge=1, le=5, description="Projected attempt number"),
    db: Session = Depends(get_db)
):
    """Uses Machine Learning to predict the likelihood of delivery failure and recommend a retry strategy."""
    from app.ml.failure_predictor import failure_predictor
    return failure_predictor.predict(db=db, target_url=target_url, attempt_number=attempt)


@router.get("/{webhook_id}", response_model=WebhookDetailResponse)
def get_webhook(webhook_id: int, db: Session = Depends(get_db)):
    """Retrieves full details of a webhook, including its complete delivery attempt timeline."""
    webhook = WebhookService.get_webhook(db, webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook with id {webhook_id} not found."
        )
    return webhook


@router.post("/{webhook_id}/retry", response_model=WebhookResponse)
def retry_webhook(webhook_id: int, db: Session = Depends(get_db)):
    """Manually re-enqueues a webhook for delivery."""
    webhook = WebhookService.retry_webhook(db, webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook with id {webhook_id} not found."
        )
    return webhook
