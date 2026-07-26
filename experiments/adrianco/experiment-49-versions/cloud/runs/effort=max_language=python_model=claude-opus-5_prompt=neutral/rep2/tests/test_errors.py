"""Tests that every failure mode leaves the API as JSON."""

from __future__ import annotations

from book_api import create_app


def test_an_unknown_route_returns_json(client):
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert response.mimetype == "application/json"
    assert response.get_json()["error"] == "not_found"


def test_an_unsupported_method_returns_json_and_an_allow_header(client, create_book):
    book = create_book()

    response = client.post("/books/{}".format(book["id"]), json={})

    assert response.status_code == 405
    assert response.get_json()["error"] == "method_not_allowed"
    assert "PUT" in response.headers["Allow"]


def test_error_bodies_always_carry_a_code_and_a_message(client):
    for response in (
        client.get("/books/999"),
        client.post("/books", json={}),
        client.get("/books?limit=nope"),
        client.get("/missing"),
    ):
        body = response.get_json()
        assert isinstance(body["error"], str) and body["error"]
        assert isinstance(body["message"], str) and body["message"]


def test_unexpected_exceptions_become_a_500_without_leaking_details():
    app = create_app({"DATABASE": ":memory:", "TESTING": False})

    @app.get("/boom")
    def boom():
        raise RuntimeError("secret internal detail")

    response = app.test_client().get("/boom")

    assert response.status_code == 500
    assert response.get_json()["error"] == "internal_error"
    assert "secret internal detail" not in response.get_data(as_text=True)


def test_the_service_keeps_working_after_a_failed_request(client, create_book):
    client.post("/books", json={"title": ""})
    client.get("/books?limit=0")

    book = create_book()

    assert client.get("/books/{}".format(book["id"])).status_code == 200
