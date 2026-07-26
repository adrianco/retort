"""Tests for the health check endpoint."""

from __future__ import annotations

import sqlite3

from bookapi import routes


def test_health_reports_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}


def test_health_reports_503_when_the_database_is_unreachable(client, monkeypatch):
    """The check is a real query, so a broken database is reported as unhealthy."""

    class BrokenConnection:
        def execute(self, *args, **kwargs):
            raise sqlite3.OperationalError("unable to open database file")

    monkeypatch.setattr(routes.db, "get_db", lambda: BrokenConnection())

    response = client.get("/health")

    assert response.status_code == 503
    assert response.get_json() == {"status": "error", "database": "unavailable"}
