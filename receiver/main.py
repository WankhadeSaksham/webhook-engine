import time
from typing import Dict, Any
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse

app = FastAPI(title="Webhook Receiver Simulator")

# In-memory counter for simulating flaky endpoints (e.g., fail 2 times, then succeed)
flaky_attempt_counters: Dict[str, int] = {}


@app.get("/")
def home():
    """Receiver health check."""
    return {
        "service": "Webhook Receiver Test Server",
        "status": "ready",
        "endpoints": {
            "POST /": "Standard receiver (200 OK)",
            "POST /success": "Always returns 200 OK",
            "POST /fail": "Always returns 500 Internal Server Error",
            "POST /slow": "Sleeps 6 seconds before responding (triggers client timeout)",
            "POST /flaky": "Fails first 2 attempts, then succeeds on attempt 3"
        }
    }


@app.post("/")
async def receive_webhook(request: Request):
    """Standard endpoint accepting webhooks."""
    headers = dict(request.headers)
    body = await request.json()
    print(f"[RECEIVER] Received webhook payload: {body}")
    print(f"[RECEIVER] Headers -> Signature: {headers.get('x-webhook-signature')}, ID: {headers.get('x-webhook-id')}")
    return {
        "status": "success",
        "message": "Webhook received successfully!",
        "received_payload": body,
        "webhook_id": headers.get("x-webhook-id"),
        "signature_present": "x-webhook-signature" in headers
    }


@app.post("/success")
async def receive_success(request: Request):
    """Guaranteed 200 OK endpoint."""
    body = await request.json()
    return {"status": "delivered", "code": 200, "payload": body}


@app.post("/fail")
async def receive_fail(request: Request):
    """Always returns 500 to simulate target service outage."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"status": "error", "error": "Simulated target database failure"}
    )


@app.post("/slow")
async def receive_slow(request: Request):
    """Simulates a sluggish endpoint that causes a client-side timeout."""
    time.sleep(6)  # Default client timeout is 5s
    return {"status": "delayed_success", "message": "Responded after 6 seconds"}


@app.post("/flaky")
async def receive_flaky(request: Request):
    """Simulates a transient error: fails the first 2 times, then succeeds on the 3rd attempt."""
    headers = dict(request.headers)
    webhook_id = headers.get("x-webhook-id", "default")
    count = flaky_attempt_counters.get(webhook_id, 0) + 1
    flaky_attempt_counters[webhook_id] = count

    if count < 3:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "transient_failure",
                "attempt_seen": count,
                "message": f"Service temporarily busy (attempt {count} failed). Retry expected!"
            }
        )
    
    # 3rd attempt succeeds!
    flaky_attempt_counters.pop(webhook_id, None)
    return {
        "status": "recovered",
        "attempt_seen": count,
        "message": "Service recovered! Webhook processed successfully."
    }