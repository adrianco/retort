"""Tests that every failure path renders as JSON in the documented shape."""

from __future__ import annotations


def test_unknown_paths_return_a_json_404(client):
    response = client.get("/not-a-real-endpoint")

    assert response.status_code == 404
    assert response.mimetype == "application/json"
    assert response.get_json()["error"] == "not_found"


def test_unsupported_methods_return_a_json_405(client, add_book):
    created = add_book()

    response = client.post(f"/books/{created['id']}", json={})

    assert response.status_code == 405
    assert response.mimetype == "application/json"
    assert response.get_json()["error"] == "method_not_allowed"


def test_oversized_bodies_are_rejected_with_a_json_413(client, app):
    payload = "x" * (app.config["MAX_CONTENT_LENGTH"] + 1)

    response = client.post("/books", data=payload, content_type="application/json")

    assert response.status_code == 413
    assert response.mimetype == "application/json"


def test_unexpected_errors_return_a_json_500_without_leaking_internals(app):
    @app.get("/boom")
    def boom():
        raise RuntimeError("secret internal detail")

    response = app.test_client().get("/boom")

    assert response.status_code == 500
    assert response.get_json() == {
        "error": "internal_error",
        "message": "An unexpected error occurred.",
    }
    assert "secret internal detail" not in response.get_data(as_text=True)


def test_error_bodies_always_carry_a_code_and_a_message(client):
    responses = [
        client.get("/books/999"),
        client.post("/books", json={}),
        client.get("/nope"),
    ]

    for response in responses:
        body = response.get_json()
        assert isinstance(body["error"], str) and body["error"]
        assert isinstance(body["message"], str) and body["message"]
