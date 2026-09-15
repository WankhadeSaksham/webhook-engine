# ⚡ Reliable Webhook Delivery & Retry Engine

An enterprise-grade, distributed webhook delivery and retry infrastructure engineered with **Python**, **FastAPI**, **Celery**, **Redis**, **PostgreSQL**, and an **Interpretable Machine Learning Failure Predictor**.

Designed to accept high-volume webhook events, persist them reliably, queue them asynchronously, execute HTTP dispatches with cryptographic HMAC signatures, automatically retry failed deliveries using exponential backoff, prevent duplicate events via idempotency, and provide real-time observability through a modern glassmorphic dashboard.

---

## 🏗️ Architecture Overview

```
                      ┌────────────────────────────────────────┐
                      │          Client Applications           │
                      └──────────────────┬─────────────────────┘
                                         │  POST /webhooks (Idempotent)
                                         ▼
                      ┌────────────────────────────────────────┐
                      │              FastAPI API               │
                      │  (Ingestion & Validation < 20ms)       │
                      └────────┬──────────────────────┬────────┘
                               │                      │
                   1. Persist  │                      │ 2. Enqueue Task
                               ▼                      ▼
                    ┌──────────────────┐    ┌──────────────────┐
                    │    PostgreSQL    │    │      Redis       │
                    │   Persistence    │    │  Message Broker  │
                    └────────▲─────────┘    └─────────┬────────┘
                             │                        │
                             │ 4. Track Attempts      │ 3. Consume Tasks
                             │                        ▼
                             │              ┌──────────────────┐
                             │              │  Celery Worker   │
                             │              │   (Solo Pool)    │
                             │              └─────────┬────────┘
                             │                        │
                             │                        │ 5. POST + HMAC-SHA256
                             │                        ▼
                             │              ┌──────────────────┐
                             └──────────────┤ Webhook Receiver │
                                            │   Target URL     │
                                            └──────────────────┘
```

---

## ✨ Core Features

1. **Decoupled Asynchronous Processing**:
   - Webhook dispatches return `201 Created` or `200 OK` in milliseconds without blocking on third-party receiver responses.
2. **Exponential Backoff Retries**:
   - Configurable backoff equation: $t = \text{base\_delay} \times 2^{\text{retry}}$ (e.g. 2s $\rightarrow$ 4s $\rightarrow$ 8s).
   - Prevents cascading thundering herd issues on struggling downstream servers.
3. **Granular Attempt & Latency Auditing**:
   - Tracks every individual HTTP attempt in `webhook_deliveries` with HTTP status code, request duration in ms, error message, and response body snippet.
4. **Guaranteed Idempotency**:
   - Clients supply an `idempotency_key` header or payload attribute. Duplicate requests return the original event without creating duplicate jobs.
5. **HMAC-SHA256 Cryptographic Signatures**:
   - Every outgoing webhook is signed with `X-Webhook-Signature: sha256=<digest>` and `X-Webhook-Timestamp` using a shared secret.
6. **Real-Time Observability Dashboard**:
   - Dark-mode glassmorphic interface with real-time delivery counts, failure metrics, auto-refreshing tables, and interactive drill-down attempt timelines.
7. **AI / ML Webhook Failure Prediction**:
   - Embedded Logistic Regression model calculating failure probabilities and prescribing dynamic backoff strategies based on historical failure rates, endpoint risk, latency, and peak traffic hours.
8. **Test Receiver Simulator**:
   - Built-in test server with `/success`, `/fail`, `/slow` (timeout testing), and `/flaky` (proves auto-recovery on 3rd attempt).

---

## 🛠️ Tech Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn, Pydantic v2
- **Database**: PostgreSQL 16, SQLAlchemy 2.0 ORM, Psycopg2-binary
- **Message Broker & Queue**: Redis 7, Celery 5.6
- **HTTP Client**: HTTPX (connection pooling and custom timeouts)
- **Machine Learning**: Pure-Python Interpretable Logistic Sigmoid Model
- **Containerization**: Docker, Docker Compose
- **Testing**: Pytest, Starlette TestClient

---

## ⚙️ Environment Configuration

Create a `.env` file in the root directory (refer to `.env.example`):

```bash
# Application
APP_ENV=development
APP_PORT=8000

# Database Configuration (PostgreSQL)
DATABASE_URL=postgresql://postgres:Doremon%40123@localhost:5432/webhook_engine

# Message Broker (Redis)
REDIS_URL=redis://localhost:6379/0

# Webhook Delivery Settings
MAX_RETRIES=3
RETRY_BASE_DELAY=2
REQUEST_TIMEOUT=5

# Security (HMAC SHA-256 signing secret)
WEBHOOK_SECRET=super_secret_webhook_signing_key_32bytes_min

# Default Receiver Target
DEFAULT_RECEIVER_URL=http://127.0.0.1:9000
```

> **Note on Special Characters**: If your PostgreSQL password contains `@`, encode it as `%40` in the connection string URL (e.g. `Doremon%40123`).

---

## 🚀 Running Locally (Step-by-Step)

### 1. Initialize Virtual Environment & Dependencies
```powershell
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run Database Migrations
Applies non-destructive schema extensions without modifying or deleting existing records:
```powershell
python -m app.database.migrations
```

### 3. Start Redis
Make sure Redis is running locally on port `6379` or via Docker:
```powershell
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

### 4. Start the Webhook Receiver Test Server (Terminal 1)
```powershell
uvicorn receiver.main:app --port 9000 --reload
```

### 5. Start the FastAPI Webhook Engine & Dashboard (Terminal 2)
```powershell
uvicorn app.main:app --port 8000 --reload
```
- **Dashboard UI**: [http://localhost:8000/dashboard](http://localhost:8000/dashboard)
- **Interactive OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 6. Start the Celery Worker (Terminal 3)
On Windows, run with the `solo` pool to avoid fork/multiprocessing constraints:
```powershell
celery -A app.workers.celery_app worker -l info -P solo
```

---

## 🐳 Running with Docker Compose

To start the entire distributed system (API, Worker, Postgres, Redis, Receiver, Dashboard) with a single command:

```powershell
docker compose up --build
```

---

## 🧪 Running Automated Tests

Run the comprehensive 15-test pytest suite covering API validation, idempotency deduplication, HMAC security, retry lifecycle, and ML failure prediction:

```powershell
pytest -v
```

---

## 📡 API Usage Examples

### Ingest a Webhook (Asynchronous)
```bash
curl -X POST http://localhost:8000/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Payment of $150.00 confirmed",
    "target_url": "http://127.0.0.1:9000/flaky",
    "event_type": "payment.success",
    "idempotency_key": "order_uuid_9921"
  }'
```
**Response (201 Created):**
```json
{
  "id": 15,
  "status": "queued",
  "message": "Webhook accepted and queued for delivery.",
  "idempotency_key": "order_uuid_9921",
  "target_url": "http://127.0.0.1:9000/flaky"
}
```

### Inspect Webhook Attempt Timeline
```bash
curl http://localhost:8000/webhooks/15
```
**Response:**
```json
{
  "id": 15,
  "message": "Payment of $150.00 confirmed",
  "status": "delivered",
  "attempts": 3,
  "deliveries": [
    {
      "attempt_number": 1,
      "status": "failed",
      "response_status_code": 503,
      "duration_ms": 18
    },
    {
      "attempt_number": 2,
      "status": "failed",
      "response_status_code": 503,
      "duration_ms": 14
    },
    {
      "attempt_number": 3,
      "status": "delivered",
      "response_status_code": 200,
      "duration_ms": 12
    }
  ]
}
```

### AI Webhook Failure Prediction
```bash
curl "http://localhost:8000/webhooks/predict-failure?target_url=http://127.0.0.1:9000/fail&attempt=2"
```
**Response:**
```json
{
  "target_url": "http://127.0.0.1:9000/fail",
  "failure_probability": 0.985,
  "success_probability": 0.015,
  "risk_level": "HIGH",
  "recommended_strategy": "Critical failure risk. Endpoint degraded or unresponsive. Apply extended backoff (15s+) or pause worker concurrency.",
  "features": {
    "attempt_number": 2,
    "recent_failure_rate": 1.0,
    "avg_latency_ms": 400.0,
    "hour_of_day_utc": 15,
    "is_peak_hour": true
  }
}
```

---

## 🔒 Security: HMAC-SHA256 Verification in Python

Receivers can authenticate that payloads originated from this engine using the shared secret:

```python
import hmac
import hashlib

def verify_webhook(raw_payload: str, signature_header: str, secret: str) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), raw_payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)
```

---

## 🔮 Future Enhancements
- Rate limiting per receiver domain using Redis Token Bucket.
- Dead Letter Queue (DLQ) persistent table with manual replay batching.
- Prometheus `/metrics` exporter and prebuilt Grafana dashboards.
