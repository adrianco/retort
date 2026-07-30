"""Tests for GET /health."""

import sqlite3

import bookapi.routes as routes


def test_health_reports_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}


def test_health_reports_503_when_database_is_unreachable(client, monkeypatch):
    def boom():
        raise sqlite3.OperationalError("unable to open database file")

    monkeypatch.setattr(routes, "get_db", boom)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.get_json()["status"] == "unhealthy"
