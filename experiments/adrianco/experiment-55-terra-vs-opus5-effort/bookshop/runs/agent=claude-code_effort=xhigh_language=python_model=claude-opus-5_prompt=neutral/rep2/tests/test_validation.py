"""Input validation: rejected payloads must not reach the database."""

import pytest

from bookapi.validation import MAX_TEXT_LENGTH, MAX_YEAR

from .conftest import GATSBY


def post(client, payload):
    return client.post("/books", json=payload)


@pytest.mark.parametrize(
    "payload, field",
    [
        ({"author": "Jane Austen"}, "title"),
        ({"title": "Emma"}, "author"),
        ({}, "title"),
        ({"title": "", "author": "Jane Austen"}, "title"),
        ({"title": "   ", "author": "Jane Austen"}, "title"),
        ({"title": "Emma", "author": ""}, "author"),
        ({"title": None, "author": "Jane Austen"}, "title"),
        ({"title": 42, "author": "Jane Austen"}, "title"),
        ({"title": "Emma", "author": ["Jane Austen"]}, "author"),
        ({"title": "x" * (MAX_TEXT_LENGTH + 1), "author": "A"}, "title"),
    ],
)
def test_invalid_title_or_author_returns_400(client, payload, field):
    response = post(client, payload)

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "Validation failed"
    assert field in body["details"]
    assert client.get("/books").get_json() == []


def test_reports_every_invalid_field_at_once(client):
    response = post(client, {"year": "recently", "isbn": "nope"})

    assert response.status_code == 400
    assert set(response.get_json()["details"]) == {"title", "author", "year", "isbn"}


@pytest.mark.parametrize(
    "year", ["recently", 19.5, True, 0, -100, MAX_YEAR + 1, [1925], {}]
)
def test_invalid_year_returns_400(client, year):
    response = post(client, {"title": "Emma", "author": "Jane Austen", "year": year})

    assert response.status_code == 400
    assert "year" in response.get_json()["details"]


@pytest.mark.parametrize("year, expected", [(1925, 1925), ("1925", 1925), (None, None)])
def test_accepted_year_values(client, year, expected):
    response = post(client, {"title": "Emma", "author": "Jane Austen", "year": year})

    assert response.status_code == 201
    assert response.get_json()["year"] == expected


@pytest.mark.parametrize("isbn", ["12345", "978074327356X", 9780743273565, "abcdefghij"])
def test_invalid_isbn_returns_400(client, isbn):
    response = post(client, {**GATSBY, "isbn": isbn})

    assert response.status_code == 400
    assert "isbn" in response.get_json()["details"]


@pytest.mark.parametrize(
    "isbn, expected",
    [
        ("9780743273565", "9780743273565"),
        ("978-0-7432-7356-5", "978-0-7432-7356-5"),
        ("043942089X", "043942089X"),
        ("", None),
        (None, None),
    ],
)
def test_accepted_isbn_values(client, isbn, expected):
    response = post(client, {**GATSBY, "isbn": isbn})

    assert response.status_code == 201
    assert response.get_json()["isbn"] == expected


@pytest.mark.parametrize("body", ["[]", '"a string"', "null", "123"])
def test_non_object_body_returns_400(client, body):
    response = client.post("/books", data=body, content_type="application/json")

    assert response.status_code == 400
    assert response.get_json()["error"] == "Request body must be a JSON object"


def test_malformed_json_returns_400(client):
    response = client.post("/books", data="{not json", content_type="application/json")

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_missing_body_returns_400(client):
    response = client.post("/books")

    assert response.status_code == 400


def test_unknown_fields_are_ignored(client):
    response = post(client, {**GATSBY, "publisher": "Scribner", "id": 999})

    assert response.status_code == 201
    book = response.get_json()
    assert "publisher" not in book
    assert book["id"] != 999
