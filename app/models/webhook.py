from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.connection import Base


class Webhook(Base):
    """Represents a webhook event that needs to be delivered."""
    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True, index=True)
    message = Column(Text, nullable=False)
    target_url = Column(String(500), nullable=False, default="http://127.0.0.1:9000")
    event_type = Column(String(50), default="default", nullable=True)
    idempotency_key = Column(String(100), unique=True, index=True, nullable=True)
    status = Column(String(20), default="pending", index=True)
    attempts = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    deliveries = relationship(
        "WebhookDelivery",
        back_populates="webhook",
        cascade="all, delete-orphan",
        order_by="WebhookDelivery.attempt_number"
    )

    def __repr__(self) -> str:
        return f"<Webhook id={self.id} status={self.status} attempts={self.attempts}>"


class WebhookDelivery(Base):
    """Represents an individual delivery attempt for a webhook."""
    __tablename__ = "webhook_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    webhook_id = Column(Integer, ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_number = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False)  # 'delivered', 'failed', 'retrying'
    response_status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, default=datetime.utcnow)

    webhook = relationship("Webhook", back_populates="deliveries")

    def __repr__(self) -> str:
        return f"<WebhookDelivery id={self.id} webhook_id={self.webhook_id} attempt={self.attempt_number} status={self.status}>"
