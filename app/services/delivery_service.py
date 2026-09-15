import json
import time
from datetime import datetime, timezone
from typing import Tuple, Optional
import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.webhook import Webhook, WebhookDelivery
from app.utils.logging import logger
from app.utils.security import generate_signature


class DeliveryService:
    """Service handling HTTP webhook dispatch, latency tracking, attempt persistence, and status updates."""

    @staticmethod
    def execute_delivery(db: Session, webhook_id: int, current_attempt: int) -> Tuple[bool, Optional[str]]:
        """Executes a single delivery attempt for the given webhook ID.
        
        Returns:
            (success: bool, error_message: Optional[str])
        """
        webhook: Optional[Webhook] = db.query(Webhook).filter(Webhook.id == webhook_id).first()
        if not webhook:
            logger.error(f"[Webhook {webhook_id}] Webhook not found in database!")
            return False, "Webhook not found"

        # Update webhook status to processing
        webhook.status = "processing"
        webhook.attempts = current_attempt
        webhook.updated_at = datetime.now(timezone.utc)
        db.commit()

        # Build payload
        payload_dict = {
            "id": webhook.id,
            "message": webhook.message,
            "event_type": webhook.event_type or "default",
            "attempt": current_attempt,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        raw_payload = json.dumps(payload_dict, separators=(",", ":"))

        # Sign payload with HMAC SHA-256
        timestamp_str = str(int(time.time()))
        signature = generate_signature(raw_payload)

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "WebhookEngine/1.0",
            "X-Webhook-ID": str(webhook.id),
            "X-Webhook-Timestamp": timestamp_str,
            "X-Webhook-Signature": signature,
        }

        logger.info(f"[Webhook {webhook.id}] Attempt {current_attempt}/{settings.max_retries} -> {webhook.target_url}")

        start_time = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        response_code: Optional[int] = None
        response_body: Optional[str] = None
        error_message: Optional[str] = None
        success = False

        try:
            with httpx.Client(timeout=httpx.Timeout(settings.request_timeout, connect=5.0)) as client:
                response = client.post(
                    webhook.target_url,
                    content=raw_payload,
                    headers=headers
                )
                response_code = response.status_code
                response_body = response.text[:1000]  # Store up to 1000 chars of body
                
                if 200 <= response.status_code < 300:
                    success = True
                    logger.info(f"[Webhook {webhook.id}] ✅ Delivered successfully! HTTP {response_code}")
                else:
                    error_message = f"HTTP Error status {response_code}"
                    logger.warning(f"[Webhook {webhook.id}] ⚠️ Receiver returned {response_code}")

        except httpx.TimeoutException as exc:
            error_message = f"Timeout ({settings.request_timeout}s): {str(exc)}"
            logger.warning(f"[Webhook {webhook.id}] ⏱️ Request timed out: {error_message}")
        except httpx.RequestError as exc:
            error_message = f"Network connection error: {str(exc)}"
            logger.warning(f"[Webhook {webhook.id}] 🔌 Connection failed: {error_message}")
        except Exception as exc:
            error_message = f"Unexpected error: {str(exc)}"
            logger.error(f"[Webhook {webhook.id}] 💥 Unexpected error: {error_message}")

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        completed_at = datetime.now(timezone.utc)

        # Record delivery attempt
        attempt_record = WebhookDelivery(
            webhook_id=webhook.id,
            attempt_number=current_attempt,
            status="delivered" if success else "failed",
            response_status_code=response_code,
            response_body=response_body,
            error_message=error_message,
            duration_ms=duration_ms,
            started_at=started_at,
            completed_at=completed_at
        )
        db.add(attempt_record)

        # Update webhook record status
        if success:
            webhook.status = "delivered"
        else:
            # If this is the last allowed attempt, mark permanently failed; otherwise retrying
            if current_attempt >= settings.max_retries:
                webhook.status = "failed"
                logger.error(f"[Webhook {webhook.id}] ❌ Permanently failed after {current_attempt} attempts.")
            else:
                webhook.status = "retrying"
                logger.info(f"[Webhook {webhook.id}] 🔁 Scheduled for retry.")

        webhook.updated_at = completed_at
        db.commit()

        return success, error_message
