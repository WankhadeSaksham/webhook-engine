import os
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.webhook_service import WebhookService

router = APIRouter(tags=["Dashboard"])

template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=template_dir)


@router.get("/dashboard", response_class=HTMLResponse)
def get_dashboard_page(request: Request, db: Session = Depends(get_db)):
    """Serves the live interactive dashboard UI."""
    metrics = WebhookService.get_metrics(db)
    webhooks, _ = WebhookService.list_webhooks(db, limit=30)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "metrics": metrics,
            "webhooks": webhooks
        }
    )


@router.get("/", response_class=HTMLResponse)
def root_redirect(request: Request, db: Session = Depends(get_db)):
    """Redirects root directly to the dashboard."""
    return get_dashboard_page(request, db)
