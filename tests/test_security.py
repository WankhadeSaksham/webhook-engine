import pytest
from app.utils.security import generate_signature, verify_signature


def test_generate_signature_format():
    payload = '{"id": 1, "message": "Test event"}'
    secret = "test_secret_key_123"
    sig = generate_signature(payload, secret)
    assert sig.startswith("sha256=")
    assert len(sig) == 7 + 64  # 'sha256=' + 64 hex chars


def test_verify_signature_valid():
    payload = '{"id": 1, "message": "Test event"}'
    secret = "test_secret_key_123"
    sig = generate_signature(payload, secret)
    assert verify_signature(payload, sig, secret) is True


def test_verify_signature_tampered_payload():
    payload = '{"id": 1, "message": "Test event"}'
    tampered_payload = '{"id": 1, "message": "Tampered event"}'
    secret = "test_secret_key_123"
    sig = generate_signature(payload, secret)
    assert verify_signature(tampered_payload, sig, secret) is False


def test_verify_signature_wrong_secret():
    payload = '{"id": 1, "message": "Test event"}'
    sig = generate_signature(payload, "secret_a")
    assert verify_signature(payload, sig, "secret_b") is False


def test_verify_signature_empty_signature():
    assert verify_signature('{"test": 1}', "") is False
