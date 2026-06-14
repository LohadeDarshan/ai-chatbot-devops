"""
Basic smoke tests for the FastAPI backend.
Run with: pytest -q (from the backend/ directory)
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    res = client.get("/")
    assert res.status_code == 200
    assert "message" in res.json()


def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert "status" in body
    assert "database" in body
    assert "model_backend" in body


def test_chat_requires_message():
    res = client.post("/api/chat", json={"session_id": "test", "message": ""})
    assert res.status_code in (400, 422)
