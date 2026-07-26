"""Tests for GET /health."""


def test_health_reports_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "connected"}


def test_health_returns_json_content_type(client):
    response = client.get("/health")

    assert response.headers["Content-Type"].startswith("application/json")
