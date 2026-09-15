from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.webhook import Webhook, WebhookDelivery
from app.schemas.webhook import WebhookCreate
from app.workers.tasks import deliver_webhook_task
from app.utils.logging import logger


class WebhookService:
    """Service managing webhook lifecycles, idempotency, queries, and metrics."""

    @staticmethod
    def create_and_enqueue_webhook(db: Session, webhook_in: WebhookCreate) -> Tuple[Webhook, bool]:
        """Creates a webhook record and enqueues delivery.
        
        If an idempotency_key is provided and already exists, returns the existing record
        without enqueuing duplicate tasks.
        
        Returns:
            (webhook: Webhook, is_duplicate: bool)
        """
        # 1. Check idempotency
        if webhook_in.idempotency_key:
            existing: Optional[Webhook] = db.query(Webhook).filter(
                Webhook.idempotency_key == webhook_in.idempotency_key
            ).first()
            if existing:
                logger.info(f"Duplicate request detected for idempotency key '{webhook_in.idempotency_key}'. Returning existing webhook #{existing.id}")
                return existing, True

        # 2. Persist new webhook
        webhook = Webhook(
            message=webhook_in.message,
            target_url=str(webhook_in.target_url),
            event_type=webhook_in.event_type or "default",
            idempotency_key=webhook_in.idempotency_key,
            status="queued",
            attempts=0
        )
        db.add(webhook)
        db.commit()
        db.refresh(webhook)

        # 3. Asynchronously enqueue task to Redis via Celery
        try:
            deliver_webhook_task.delay(webhook.id)
            logger.info(f"Enqueued webhook #{webhook.id} to Celery worker queue.")
        except Exception as exc:
            logger.error(f"Failed to enqueue webhook #{webhook.id} to Celery: {exc}")
            # If Redis is temporarily down, it stays in 'queued' or 'pending' state
            webhook.status = "pending"
            db.commit()

        return webhook, False

    @staticmethod
    def get_webhook(db: Session, webhook_id: int) -> Optional[Webhook]:
        """Retrieves a single webhook by ID with full delivery attempts."""
        return db.query(Webhook).filter(Webhook.id == webhook_id).first()

    @staticmethod
    def list_webhooks(
        db: Session,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Webhook], int]:
        """Lists webhooks with optional status filtering and pagination."""
        query = db.query(Webhook)
        if status:
            query = query.filter(Webhook.status == status)
        
        total = query.count()
        webhooks = query.order_by(Webhook.id.desc()).offset(offset).limit(limit).all()
        return webhooks, total

    @staticmethod
    def retry_webhook(db: Session, webhook_id: int) -> Optional[Webhook]:
        """Manually triggers a retry for an existing webhook."""
        webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
        if not webhook:
            return None
        
        webhook.status = "queued"
        db.commit()
        db.refresh(webhook)
        
        deliver_webhook_task.delay(webhook.id)
        logger.info(f"Manual retry initiated for webhook #{webhook.id}")
        return webhook

    @staticmethod
    def get_metrics(db: Session) -> dict:
        """Aggregates system-wide delivery performance and status metrics."""
        total_webhooks = db.query(Webhook).count()
        status_counts = dict(
            db.query(Webhook.status, func.count(Webhook.id))
            .group_by(Webhook.status)
            .all()
        )
        total_attempts = db.query(WebhookDelivery).count()
        successful_attempts = db.query(WebhookDelivery).filter(WebhookDelivery.status == "delivered").count()
        
        success_rate = 0.0
        if total_attempts > 0:
            success_rate = round((successful_attempts / total_attempts) * 100, 2)

        return {
            "total_webhooks": total_webhooks,
            "queued": status_counts.get("queued", 0),
            "pending": status_counts.get("pending", 0),
            "processing": status_counts.get("processing", 0),
            "delivered": status_counts.get("delivered", 0),
            "retrying": status_counts.get("retrying", 0),
            "failed": status_counts.get("failed", 0),
            "total_attempts": total_attempts,
            "success_rate_percent": success_rate,
        }
