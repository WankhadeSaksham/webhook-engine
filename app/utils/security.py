import hmac
import hashlib
from typing import Tuple
from app.config import settings


def generate_signature(payload: str, secret: str = None) -> str:
    """Generate an HMAC-SHA256 signature for a webhook payload string."""
    signing_secret = secret or settings.webhook_secret
    signature = hmac.new(
        key=signing_secret.encode("utf-8"),
        msg=payload.encode("utf-8"),
        digestmod=hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"


def verify_signature(payload: str, header_signature: str, secret: str = None) -> bool:
    """Verify incoming HMAC-SHA256 signature using constant-time comparison to prevent timing attacks."""
    if not header_signature:
        return False
        
    expected_signature = generate_signature(payload, secret)
    return hmac.compare_digest(expected_signature, header_signature)
