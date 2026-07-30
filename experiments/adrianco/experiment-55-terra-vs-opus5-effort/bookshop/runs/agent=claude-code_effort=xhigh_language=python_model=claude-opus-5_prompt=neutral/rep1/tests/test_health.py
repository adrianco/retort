"""Health check and service index."""

from __future__ import annotations

import sqlite3
from unittest.mock import patch


def test_health_reports_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.mimetype == "application/json"
    body = response.get_json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["books"] == 0


def test_health_counts_stored_books(client, create_book):
    create_book()
    create_book(title="Animal Farm", isbn=None)

    assert client.get("/health").get_json()["books"] == 2


def test_health_reports_503_when_database_is_unreachable(client):
    with patch("bookapi.routes.repository.count_books",
               side_effect=sqlite3.OperationalError("disk I/O error")):
        response = client.get("/health")

    assert response.status_code == 503
    assert response.get_json()["status"] == "unhealthy"
    assert response.get_json()["database"] == "unavailable"


def test_index_lists_endpoints(client):
    body = client.get("/").get_json()

    assert body["service"] == "book-collection-api"
    assert body["endpoints"]["create_book"] == "POST /books"
