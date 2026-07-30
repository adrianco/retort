"""The health check endpoint."""

from __future__ import annotations

from bookapi import __version__


def test_health_reports_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ok",
        "database": "ok",
        "books": 0,
        "version": __version__,
    }


def test_health_counts_the_collection(client, library):
    assert client.get("/health").get_json()["books"] == len(library)


def test_health_reports_503_when_the_database_is_unreachable(app, client):
    app.config["DATABASE"] = "/nonexistent-directory-xyz/books.db"

    response = client.get("/health")

    assert response.status_code == 503
    body = response.get_json()
    assert body["status"] == "unhealthy"
    assert body["database"] == "unavailable"


def test_root_lists_the_available_endpoints(client):
    response = client.get("/")

    assert response.status_code == 200
    endpoints = response.get_json()["endpoints"]
    assert endpoints == {
        "health": "/health",
        "books": "/books",
        "openapi": "/openapi.json",
    }
