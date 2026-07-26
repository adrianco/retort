"""Tests for GET /health and the API index."""

from __future__ import annotations

import sqlite3

from book_api import __version__
from book_api.repository import BookRepository


def test_health_reports_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.mimetype == "application/json"
    body = response.get_json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["version"] == __version__
    assert body["books"] == 0
    assert body["time"].endswith("Z")


def test_health_counts_the_stored_books(client, library):
    body = client.get("/health").get_json()

    assert body["books"] == len(library)


def test_health_reports_503_when_the_database_is_unreachable(client, monkeypatch):
    def explode(self):
        raise sqlite3.OperationalError("no such table: books")

    monkeypatch.setattr(BookRepository, "total", explode)

    response = client.get("/health")

    assert response.status_code == 503
    body = response.get_json()
    assert body["status"] == "unavailable"
    assert body["database"] == "error"
    # The driver message is logged, never returned.
    assert "no such table" not in response.get_data(as_text=True)


def test_index_documents_the_available_endpoints(client):
    response = client.get("/")

    assert response.status_code == 200
    body = response.get_json()
    assert body["service"] == "book-api"
    assert body["endpoints"]["create_book"] == "POST /books"
