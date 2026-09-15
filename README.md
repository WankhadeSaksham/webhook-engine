# Reliable Webhook Delivery & Retry Engine

A production-inspired asynchronous webhook delivery and retry engine built with **Python, FastAPI, Celery, Redis, and PostgreSQL**.

The system reliably delivers webhooks to external services, handles temporary failures through configurable retries, tracks delivery attempts, provides webhook security through HMAC signatures, and exposes delivery information through a monitoring dashboard.

> 🚀 Built as a hands-on project to explore asynchronous processing, distributed systems, reliable delivery patterns, and backend engineering.

---

## ✨ Features

* 🔗 **Asynchronous Webhook Delivery**
* 🔄 **Automatic Retry Mechanism**
* 📈 **Exponential Backoff**
* ⚡ **Redis + Celery Task Queue**
* 🐘 **PostgreSQL Persistence**
* 🔐 **HMAC-SHA256 Webhook Signing**
* 🛡️ **Idempotency Support**
* 📊 **Delivery & Attempt Tracking**
* 🚦 **Configurable Retry Policies**
* 🧪 **Test Receiver with Failure Simulation**
* 📡 **Health & System Monitoring**
* 📋 **Delivery Dashboard**
* 🐳 **Docker & Docker Compose Support**
* 🧪 **Automated Testing with Pytest**
* 🤖 **Experimental Failure-Risk Prediction Module**

---

# 🏗️ Architecture

```text
                         ┌────────────────────┐
                         │      Client        │
                         │  Create Webhook    │
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │      FastAPI       │
                         │   API / Ingestion  │
                         └─────────┬──────────┘
                                   │
                         ┌─────────▼──────────┐
                         │    PostgreSQL      │
                         │  Webhook Metadata  │
                         │ Delivery Attempts  │
                         └────────────────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │       Redis        │
                         │    Task Broker     │
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │   Celery Worker    │
                         │ Webhook Dispatcher │
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │  External Receiver │
                         └─────────┬──────────┘
                                   │
                         ┌─────────┴──────────┐
                         │                    │
                      Success              Failure
                         │                    │
                         ▼                    ▼
                    Mark Success       Retry with
                                       Backoff
                                            │
                                            ▼
                                      Celery Queue
```

---

# 🔄 How It Works

### 1. Webhook Creation

A client sends a request to the FastAPI backend containing the webhook destination and payload.

### 2. Validation

The API validates the incoming request and stores the webhook information in PostgreSQL.

### 3. Task Queuing

Instead of blocking the API request while waiting for the destination server, the delivery task is placed into Redis through Celery.

### 4. Webhook Delivery

A Celery worker retrieves the task and sends the webhook request to the destination.

### 5. Failure Handling

If the receiver is unavailable or returns a failure response, the system records the failed attempt.

### 6. Retry

The delivery is retried according to the configured retry policy using exponential backoff.

Example:

```text
Attempt 1
   ↓
Failure
   ↓
Wait
   ↓
Attempt 2
   ↓
Failure
   ↓
Longer Wait
   ↓
Attempt 3
   ↓
Success / Final Failure
```

### 7. Tracking

Each delivery attempt is stored so that the system can track:

* Delivery status
* Attempt number
* Response status
* Error information
* Timestamps
* Retry information

---

# 🧰 Tech Stack

| Technology         | Purpose                         |
| ------------------ | ------------------------------- |
| **Python**         | Core application logic          |
| **FastAPI**        | REST API                        |
| **Celery**         | Background task processing      |
| **Redis**          | Message broker / task queue     |
| **PostgreSQL**     | Persistent data storage         |
| **Docker**         | Containerization                |
| **Docker Compose** | Local multi-service environment |
| **Pytest**         | Automated testing               |

---

# 📁 Project Structure

```text
webhook-engine/
│
├── sender/
│   └── main.py
│
├── receiver/
│   └── ...
│
├── database/
│   └── ...
│
├── tests/
│   └── ...
│
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

> The exact structure may evolve as the project develops.

---

# 🚀 Getting Started

## Prerequisites

Make sure you have the following installed:

* Python 3.11+
* Docker Desktop
* Git

---

## 1. Clone the Repository

```bash
git clone https://github.com/WankhadeSaksham/webhook-engine.git
cd webhook-engine
```

---

## 2. Create a Virtual Environment

### Windows

```bash
python -m venv venv
```

Activate it:

```bash
venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure Environment Variables

Create a `.env` file from `.env.example`.

```bash
copy .env.example .env
```

Then configure your local environment.

Example:

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/webhook_engine

REDIS_URL=redis://localhost:6379/0
```

> ⚠️ Never commit your `.env` file or real credentials to GitHub.

---

# 🐳 Run with Docker

Start the required services:

```bash
docker compose up -d
```

Check running containers:

```bash
docker compose ps
```

To stop the services:

```bash
docker compose down
```

---

# ▶️ Running the Application

Start the FastAPI server:

```bash
uvicorn app.main:app --reload
```

Depending on the project entry point, the command may vary.

Open the API documentation:

```text
http://localhost:8000/docs
```

FastAPI provides interactive Swagger documentation for testing the available endpoints.

---

# 🧪 Testing

Run the test suite with:

```bash
pytest
```

The tests cover important webhook delivery and retry behaviour.

Example scenarios include:

* Successful delivery
* Failed delivery
* Retry behaviour
* Receiver unavailable
* Idempotency
* Webhook signing
* Delivery tracking

---

# 🧪 Test Receiver

The project includes a test receiver that can simulate different receiver behaviours.

This allows the retry system to be tested under realistic failure conditions.

Example scenarios:

```text
Successful Receiver
        ↓
HTTP 2xx
        ↓
Delivery succeeds
```

```text
Failing Receiver
        ↓
HTTP failure
        ↓
Retry
        ↓
Retry
        ↓
Final status
```

```text
Slow Receiver
        ↓
Timeout
        ↓
Retry
```

```text
Flaky Receiver
        ↓
Failure
        ↓
Retry
        ↓
Success
```

---

# 🔐 Webhook Security

The system supports **HMAC-SHA256 signatures** to help receivers verify that webhook requests were generated by the sender.

Conceptually:

```text
Webhook Payload
      +
Secret Key
      ↓
HMAC-SHA256
      ↓
Signature
      ↓
Receiver Verification
```

This helps protect webhook communication from unauthorized or tampered requests.

---

# 🛡️ Idempotency

Webhook delivery systems can sometimes process the same event more than once.

The project includes idempotency handling to reduce duplicate processing.

A unique identifier can be associated with an event so that repeated requests can be recognized.

```text
Event ID
   ↓
Already Processed?
   ├── Yes → Avoid duplicate processing
   │
   └── No  → Process event
```

---

# 🔄 Retry Strategy

Temporary failures should not immediately result in permanent delivery failure.

The retry system uses an exponential-backoff approach.

Conceptually:

```text
Attempt 1 → Failure
              ↓
            Wait

Attempt 2 → Failure
              ↓
         Longer Wait

Attempt 3 → Failure
              ↓
          Final Status
```

The exact retry configuration can be adjusted according to the application's requirements.

---

# 📊 Monitoring

The application tracks webhook delivery information such as:

* Current delivery status
* Number of attempts
* HTTP response status
* Error information
* Delivery timestamps
* Retry information

This information can be used by the dashboard to understand the state of webhook deliveries.

---

# 🤖 Failure-Risk Prediction

The project also contains an **experimental failure-risk prediction module**.

Its purpose is to explore how historical delivery information could potentially be used to estimate the likelihood of future webhook failures.

This component is experimental and should not be considered a production-grade ML model.

---

# 📸 Demo

> Add screenshots or a short GIF/video of the application here.

Recommended demo flow:

```text
Create Webhook
      ↓
Send Event
      ↓
Receiver Fails
      ↓
Automatic Retry
      ↓
Receiver Recovers
      ↓
Successful Delivery
      ↓
Dashboard Updates
```

---

# 📌 Example Use Cases

Webhook infrastructure like this can be useful for systems such as:

* Payment notifications
* Order updates
* User events
* CI/CD notifications
* SaaS integrations
* Third-party API integrations
* Event-driven applications
* Microservice communication

---

# 🧠 What I Learned

Building this project helped me understand practical backend and distributed-system concepts including:

* Asynchronous task processing
* Message queues
* Redis
* Celery workers
* PostgreSQL persistence
* Webhook architecture
* Retry strategies
* Exponential backoff
* Idempotency
* HMAC authentication
* Failure handling
* Docker-based development
* Automated testing
* Monitoring and delivery tracking
* Designing reliable backend services

---

# 🔮 Future Improvements

Possible future improvements include:

* [ ] GitHub Actions CI/CD
* [ ] Better authentication and authorization
* [ ] Rate limiting
* [ ] Dead-letter queue
* [ ] More advanced retry policies
* [ ] Improved dashboard and analytics
* [ ] Prometheus metrics
* [ ] Grafana monitoring
* [ ] Distributed tracing
* [ ] More comprehensive integration tests
* [ ] Load testing and benchmark results
* [ ] Webhook subscription management
* [ ] Multi-tenant support

---

# ⚠️ Security

Never commit sensitive information such as:

```text
.env
API keys
Database passwords
Redis credentials
Private tokens
Secret keys
```

Use `.env` for local secrets and commit only `.env.example`.

---

# 📄 License

This project is currently intended as a learning and portfolio project.

If this repository is later distributed as open-source software, an appropriate open-source license will be added.

---

# 👨‍💻 Author

**Saksham Wankhade**

AIML Student | Python Developer | AI/ML & Backend Enthusiast

GitHub:
https://github.com/WankhadeSaksham

---

## ⭐ If you find this project interesting

Feel free to explore the code, experiment with the webhook receiver, and check out the retry and delivery mechanisms.

Built with Python, curiosity, and a lot of debugging. 🚀
