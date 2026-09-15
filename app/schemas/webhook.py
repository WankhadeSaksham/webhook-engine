from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, HttpUrl, Field, ConfigDict


class WebhookCreate(BaseModel):
    """Schema for incoming webhook dispatch requests."""
    message: str = Field(..., min_length=1, description="Payload content or event message")
    target_url: HttpUrl = Field(
        default="http://127.0.0.1:9000",
        description="Destination URL for webhook delivery"
    )
    event_type: Optional[str] = Field(default="default", description="Event category (e.g., payment.success)")
    idempotency_key: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Client-provided unique key to prevent duplicate webhook dispatches"
    )


class WebhookCreateResponse(BaseModel):
    """Immediate response returned after queueing the webhook."""
    id: int
    status: str
    message: str
    idempotency_key: Optional[str] = None
    target_url: str


class WebhookDeliveryResponse(BaseModel):
    """Schema representing an individual delivery attempt."""
    id: int
    webhook_id: int
    attempt_number: int
    status: str
    response_status_code: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    started_at: datetime
    completed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WebhookResponse(BaseModel):
    """Schema for a webhook record."""
    id: int
    message: str
    target_url: str
    event_type: Optional[str] = None
    idempotency_key: Optional[str] = None
    status: str
    attempts: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WebhookDetailResponse(WebhookResponse):
    """Schema for a webhook including its full delivery attempt timeline."""
    deliveries: List[WebhookDeliveryResponse] = []
