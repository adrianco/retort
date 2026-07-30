"""Health check and framework-level error shape."""

from __future__ import annotations

import pytest

from bookapi import create_app


def test_health_reports_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}


def test_health_reports_503_when_database_is_unusable(app, tmp_path):
    # A directory is a path sqlite can never open, which is what a broken
    # volume looks like from inside the request.
    unusable = tmp_path / "not-a-file"
    unusable.mkdir()
    app.config["DATABASE"] = str(unusable)

    response = app.test_client().get("/health")

    assert response.status_code == 503
    body = response.get_json()
    assert body["status"] == "error"
    assert body["database"] == "unavailable"


def test_health_reports_503_when_the_parent_directory_cannot_be_created(
    app, tmp_path
):
    """Opening the DB may first mkdir its parent, which raises OSError, not
    sqlite3.Error -- a different failure branch from an unopenable file."""
    blocker = tmp_path / "a-regular-file"
    blocker.write_text("not a directory")
    app.config["DATABASE"] = str(blocker / "sub" / "books.db")

    response = app.test_client().get("/health")

    assert response.status_code == 503
    assert response.get_json()["database"] == "unavailable"


def test_unknown_route_returns_json_not_html(client):
    response = client.get("/nope")

    assert response.status_code == 404
    assert response.mimetype == "application/json"
    assert response.get_json()["error"]["code"] == "not_found"


def test_wrong_method_returns_json_405_and_keeps_allow_header(client):
    response = client.patch("/books")

    assert response.status_code == 405
    assert response.mimetype == "application/json"
    assert response.get_json()["error"]["code"] == "method_not_allowed"
    assert "POST" in response.headers["Allow"]


def test_unexpected_error_propagates_under_testing(app):
    """A bug in a handler must surface as a traceback in tests, not a bland 500."""

    @app.get("/boom")
    def boom():
        raise RuntimeError("kaboom")

    with pytest.raises(RuntimeError, match="kaboom"):
        app.test_client().get("/boom")


def test_unexpected_error_returns_json_500(db_path):
    app = create_app(
        # Mirror production: do not re-raise, render the JSON envelope.
        {"DATABASE": str(db_path), "TESTING": True, "PROPAGATE_EXCEPTIONS": False}
    )

    @app.get("/boom")
    def boom():
        raise RuntimeError("kaboom")

    response = app.test_client().get("/boom")

    assert response.status_code == 500
    assert response.get_json() == {
        "error": {"code": "internal_error", "message": "Internal server error."}
    }
