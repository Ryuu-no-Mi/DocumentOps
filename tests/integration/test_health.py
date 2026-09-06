"""Integration tests for API endpoints."""

from fastapi.testclient import TestClient

from documentops.api.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    """Health endpoint should return ok status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "documentops-api"}


def test_root_endpoint() -> None:
    """Root endpoint should return service info."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "DocumentOps API"
    assert response.json()["version"] == "0.1.0"
