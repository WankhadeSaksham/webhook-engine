import pytest
from app.database.connection import SessionLocal
from app.ml.failure_predictor import failure_predictor


def test_failure_predictor_initialization():
    assert failure_predictor.is_trained is True
    assert failure_predictor.weights is not None
    assert failure_predictor.intercept is not None


def test_failure_predictor_healthy_endpoint():
    db = SessionLocal()
    try:
        result = failure_predictor.predict(
            db=db,
            target_url="http://127.0.0.1:9000/success",
            attempt_number=1
        )
        assert "failure_probability" in result
        assert "risk_level" in result
        assert "recommended_strategy" in result
        assert 0.0 <= result["failure_probability"] <= 1.0
        # Healthy attempt 1 should typically be lower risk
        assert result["risk_level"] in ["LOW", "MEDIUM"]
    finally:
        db.close()


def test_failure_predictor_failing_endpoint():
    db = SessionLocal()
    try:
        result = failure_predictor.predict(
            db=db,
            target_url="http://127.0.0.1:9000/fail",
            attempt_number=3
        )
        assert result["failure_probability"] >= 0.5
        assert result["risk_level"] in ["MEDIUM", "HIGH"]
    finally:
        db.close()
