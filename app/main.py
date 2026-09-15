from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.webhooks import router as webhooks_router
from app.api.dashboard import router as dashboard_router
from app.config import settings

app = FastAPI(
    title="Reliable Webhook Delivery & Retry Engine",
    description="Enterprise-grade distributed webhook ingestion, dispatch, exponential backoff retries, HMAC security, and observability.",
    version="1.0.0"
)

# Enable CORS for frontend and external clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API and Dashboard Routers
app.include_router(webhooks_router)
app.include_router(dashboard_router)


@app.get("/health")
def health_check():
    """System health check endpoint."""
    return {
        "status": "healthy",
        "service": "webhook-engine",
        "version": "1.0.0",
        "environment": settings.app_env
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.app_port, reload=True)
