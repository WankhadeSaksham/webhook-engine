from celery.exceptions import MaxRetriesExceededError
from app.workers.celery_app import celery_app
from app.database.connection import SessionLocal
from app.services.delivery_service import DeliveryService
from app.config import settings
from app.utils.logging import logger


@celery_app.task(bind=True, name="app.workers.tasks.deliver_webhook_task")
def deliver_webhook_task(self, webhook_id: int) -> dict:
    """Celery background worker task for reliable webhook delivery with exponential backoff."""
    current_attempt = self.request.retries + 1
    db = SessionLocal()
    
    try:
        success, error_msg = DeliveryService.execute_delivery(
            db=db,
            webhook_id=webhook_id,
            current_attempt=current_attempt
        )
        
        if success:
            return {"webhook_id": webhook_id, "status": "delivered", "attempt": current_attempt}

        # If delivery failed and we have retries remaining, calculate exponential backoff delay
        if current_attempt < settings.max_retries:
            # Exponential backoff formula: base_delay * (2 ** retries)
            # Retries=0 -> 2s, Retries=1 -> 4s, etc.
            backoff_delay = settings.retry_base_delay * (2 ** self.request.retries)
            logger.info(
                f"[Worker Webhook {webhook_id}] Retrying in {backoff_delay}s "
                f"(Attempt {current_attempt}/{settings.max_retries})"
            )
            raise self.retry(
                exc=Exception(error_msg or "Delivery attempt failed"),
                countdown=backoff_delay,
                max_retries=settings.max_retries - 1
            )
        else:
            logger.error(f"[Worker Webhook {webhook_id}] Max retries reached ({settings.max_retries}). Giving up.")
            return {"webhook_id": webhook_id, "status": "failed", "attempt": current_attempt, "error": error_msg}

    except MaxRetriesExceededError:
        logger.error(f"[Worker Webhook {webhook_id}] Max retries exceeded.")
        return {"webhook_id": webhook_id, "status": "failed", "attempt": current_attempt}
    finally:
        db.close()
