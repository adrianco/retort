"""Integration tests for the book collection API."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402

SAMPLE = {
    "title": "Dune",
    "author": "Frank Herbert",
    "year": 1965,
    "isbn": "9780441013593",
}


@pytest.fixture
def client(tmp_path):
    app = create_app(database=str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def create(client, **overrides):
    payload = {**SAMPLE, **overrides}
    resp = client.post("/books", json=payload)
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok", "database": "ok"}


def test_create_book_returns_201_with_id_and_location(client):
    resp = client.post("/books", json=SAMPLE)
    assert resp.status_code == 201
    body = resp.get_json()
    assert isinstance(body["id"], int)
    assert {k: body[k] for k in SAMPLE} == SAMPLE
    assert resp.headers["Location"] == f"/books/{body['id']}"


def test_create_book_allows_optional_fields_to_be_omitted(client):
    resp = client.post("/books", json={"title": "Untitled", "author": "Anon"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["year"] is None
    assert body["isbn"] is None


@pytest.mark.parametrize(
    "payload, expected_detail",
    [
        ({"author": "Frank Herbert"}, "title is required"),
        ({"title": "Dune"}, "author is required"),
        ({"title": "   ", "author": "Anon"}, "title must not be empty"),
        ({"title": "Dune", "author": 42}, "author must be a string"),
        ({"title": "Dune", "author": "Anon", "year": "1965"}, "year must be an integer"),
    ],
)
def test_create_book_validation_errors(client, payload, expected_detail):
    resp = client.post("/books", json=payload)
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["error"] == "validation failed"
    assert expected_detail in body["details"]


def test_create_book_rejects_non_json_body(client):
    resp = client.post("/books", data="not json", content_type="text/plain")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation failed"


def test_list_books_returns_all_books_in_id_order(client):
    first = create(client)
    second = create(client, title="Neuromancer", author="William Gibson", year=1984)

    resp = client.get("/books")
    assert resp.status_code == 200
    assert [b["id"] for b in resp.get_json()] == [first["id"], second["id"]]


def test_list_books_filters_by_author_case_insensitively(client):
    create(client)
    create(client, title="Neuromancer", author="William Gibson", year=1984)

    resp = client.get("/books?author=frank herbert")
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body) == 1
    assert body[0]["title"] == "Dune"

    assert client.get("/books?author=Nobody").get_json() == []


def test_get_book_by_id(client):
    book = create(client)
    resp = client.get(f"/books/{book['id']}")
    assert resp.status_code == 200
    assert resp.get_json() == book


def test_get_missing_book_returns_404(client):
    resp = client.get("/books/9999")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "book not found"}


def test_update_book_replaces_fields(client):
    book = create(client)
    resp = client.put(
        f"/books/{book['id']}",
        json={"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969},
    )
    assert resp.status_code == 200
    assert resp.get_json() == {
        "id": book["id"],
        "title": "Dune Messiah",
        "author": "Frank Herbert",
        "year": 1969,
        "isbn": None,
    }
    # The change is persisted, not just echoed back.
    assert client.get(f"/books/{book['id']}").get_json()["title"] == "Dune Messiah"


def test_update_book_validates_payload(client):
    book = create(client)
    resp = client.put(f"/books/{book['id']}", json={"author": "Frank Herbert"})
    assert resp.status_code == 400
    assert "title is required" in resp.get_json()["details"]


def test_update_missing_book_returns_404(client):
    resp = client.put("/books/9999", json=SAMPLE)
    assert resp.status_code == 404


def test_delete_book_returns_204_and_removes_it(client):
    book = create(client)
    resp = client.delete(f"/books/{book['id']}")
    assert resp.status_code == 204
    assert resp.get_data() == b""
    assert client.get(f"/books/{book['id']}").status_code == 404


def test_delete_missing_book_returns_404(client):
    resp = client.delete("/books/9999")
    assert resp.status_code == 404


def test_unknown_route_returns_json_404(client):
    resp = client.get("/nope")
    assert resp.status_code == 404
    assert resp.is_json
    assert "error" in resp.get_json()
