"""Input validation: bad requests must be rejected, not stored."""

from __future__ import annotations

import pytest

from tests.conftest import SAMPLE

INVALID_BODIES = [
    pytest.param({"author": "Frank Herbert"}, "title", id="missing-title"),
    pytest.param({"title": "Dune"}, "author", id="missing-author"),
    pytest.param({"title": "", "author": "FH"}, "title", id="empty-title"),
    pytest.param({"title": "   ", "author": "FH"}, "title", id="whitespace-title"),
    pytest.param({"title": "Dune", "author": ""}, "author", id="empty-author"),
    pytest.param({"title": None, "author": "FH"}, "title", id="null-title"),
    pytest.param({"title": "Dune", "author": "FH", "year": "soon"}, "year", id="year-not-a-number"),
    pytest.param({"title": "Dune", "author": "FH", "year": 0}, "year", id="year-too-small"),
    pytest.param({"title": "Dune", "author": "FH", "year": 99999}, "year", id="year-too-large"),
    pytest.param({"title": "Dune", "author": "FH", "isbn": "123"}, "isbn", id="isbn-too-short"),
    pytest.param({"title": "x" * 501, "author": "FH"}, "title", id="title-too-long"),
]


@pytest.mark.parametrize(("payload", "field"), INVALID_BODIES)
def test_create_rejects_invalid_payload(client, payload, field):
    response = client.post("/books", json=payload)

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["error"] == "validation_error"
    assert field in [detail["field"] for detail in body["details"]]
    assert client.get("/books").json() == []  # nothing was stored


@pytest.mark.parametrize(("payload", "field"), INVALID_BODIES)
def test_update_rejects_invalid_payload(client, make_book, payload, field):
    created = make_book()

    response = client.put(f"/books/{created['id']}", json=payload)

    assert response.status_code == 400, response.text
    assert field in [detail["field"] for detail in response.json()["details"]]
    assert client.get(f"/books/{created['id']}").json() == created  # unchanged


def test_unknown_fields_are_rejected(client):
    response = client.post("/books", json={**SAMPLE, "publisher": "Chilton"})

    assert response.status_code == 400
    assert "publisher" in [detail["field"] for detail in response.json()["details"]]


def test_malformed_json_returns_400(client):
    response = client.post(
        "/books", content=b"{not json", headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 400
    assert response.json()["error"] == "validation_error"


def test_surrounding_whitespace_is_trimmed(client):
    response = client.post("/books", json={"title": "  Dune  ", "author": " Frank Herbert "})

    assert response.status_code == 201
    assert response.json()["title"] == "Dune"
    assert response.json()["author"] == "Frank Herbert"


@pytest.mark.parametrize(
    ("supplied", "stored"),
    [
        ("978-0441013593", "9780441013593"),
        ("9780441013593", "9780441013593"),
        ("0-441-01359-1", "0441013591"),
        ("080442957x", "080442957X"),
    ],
)
def test_valid_isbn_formats_are_normalised(client, supplied, stored):
    response = client.post("/books", json={"title": "T", "author": "A", "isbn": supplied})

    assert response.status_code == 201, response.text
    assert response.json()["isbn"] == stored


def test_unknown_route_returns_a_structured_404(client):
    response = client.get("/nope")

    assert response.status_code == 404
    assert response.json()["error"] == "not_found"
