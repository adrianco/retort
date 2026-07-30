"""Every failure path answers with JSON, never an HTML error page."""

from __future__ import annotations

import json

import pytest


def assert_json_error(response, *, status, code=None):
    assert response.status_code == status
    assert response.mimetype == "application/json"
    body = response.get_json()
    assert isinstance(body["error"], str) and body["error"]
    assert isinstance(body["code"], str) and body["code"]
    if code is not None:
        assert body["code"] == code
    return body


def test_unknown_route_returns_json_404(client):
    assert_json_error(client.get("/does-not-exist"), status=404, code="not_found")


def test_wrong_method_returns_json_405_with_allow_header(client, book):
    response = client.post(f"/books/{book['id']}", json={})

    assert_json_error(response, status=405, code="method_not_allowed")
    allowed = {method.strip() for method in response.headers["Allow"].split(",")}
    assert {"GET", "PUT", "PATCH", "DELETE"} <= allowed


def test_malformed_json_body_returns_400(client):
    response = client.post(
        "/books", data="{not json", content_type="application/json"
    )

    assert_json_error(response, status=400, code="validation_error")


def test_missing_body_returns_400(client):
    assert_json_error(client.post("/books"), status=400, code="validation_error")


@pytest.mark.parametrize("body", ["[]", '"a string"', "42", "null", "true"])
def test_json_body_that_is_not_an_object_returns_400(client, body):
    response = client.post("/books", data=body, content_type="application/json")

    assert_json_error(response, status=400, code="validation_error")


def test_body_is_parsed_even_without_a_json_content_type(client):
    response = client.post(
        "/books",
        data=json.dumps({"title": "Dune", "author": "Frank Herbert"}),
        content_type="text/plain",
    )

    assert response.status_code == 201
    assert response.get_json()["title"] == "Dune"


@pytest.mark.parametrize("path", ["/books/abc", "/books/1.5", "/books/-1", "/books/"])
def test_non_integer_book_id_returns_json_404(client, path):
    assert_json_error(client.get(path), status=404)


def _call(client, method, path):
    body = {"json": {"title": "T", "author": "A"}} if method in ("put", "patch") else {}
    return getattr(client, method)(path, **body)


@pytest.mark.parametrize("method", ["get", "put", "patch", "delete"])
def test_operations_on_a_missing_book_return_404(client, method):
    response = _call(client, method, "/books/999999")

    assert_json_error(response, status=404, code="not_found")


@pytest.mark.parametrize("method", ["get", "put", "patch", "delete"])
@pytest.mark.parametrize("book_id", [2**63, 2**63 + 1, 10**25])
def test_book_id_beyond_sqlites_range_is_404_on_every_verb(client, method, book_id):
    """Such an id cannot be bound as a parameter, so it used to reach sqlite3 and
    surface as a 500.  Screening it in the view (rather than as int(max=...) on
    the rule) is what keeps the answer 404 rather than 405 for PUT/PATCH/DELETE.
    """
    assert_json_error(
        _call(client, method, f"/books/{book_id}"), status=404, code="not_found"
    )


@pytest.mark.parametrize("method", ["get", "put", "patch", "delete"])
def test_the_largest_bindable_book_id_still_reaches_the_database(client, method):
    """One below the ceiling must be a normal lookup, not a rejected id."""
    assert_json_error(
        _call(client, method, f"/books/{2**63 - 1}"), status=404, code="not_found"
    )


def test_unreachable_database_surfaces_as_json_not_a_traceback(app, client):
    app.config["DATABASE"] = "/nonexistent-directory-xyz/books.db"

    body = assert_json_error(client.get("/books"), status=500, code="internal_error")
    # sqlite3's own message ("unable to open database file") must not be relayed:
    # the client gets a fixed sentence, and the detail goes to the log instead.
    assert body == {
        "error": "The server encountered an internal error.",
        "code": "internal_error",
    }


def test_error_payloads_never_leak_internals(client):
    body = client.get("/books/999999").get_json()

    assert set(body) <= {"error", "code", "details"}
