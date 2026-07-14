"""Test suite for Book API REST Service."""
import pytest
import json


class TestHealthCheck:
    """Tests for the health check endpoint: GET /health"""

    def test_health_check_returns_200(self, app):
        """GET /health should return HTTP 200."""
        _, client = app
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_returns_json(self, app):
        """GET /health should return JSON content type."""
        _, client = app
        response = client.get("/health")
        assert response.content_type == "application/json"

    def test_health_check_returns_status_ok(self, app):
        """GET /health should return {"status": "ok"}."""
        _, client = app
        response = client.get("/health")
        data = response.get_json()
        assert data is not None
        assert data["status"] == "ok"
