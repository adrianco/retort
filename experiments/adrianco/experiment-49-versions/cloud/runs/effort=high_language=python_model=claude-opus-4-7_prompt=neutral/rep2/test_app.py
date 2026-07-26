import os
import tempfile

import pytest

from app import create_app


@pytest.fixture()
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app = create_app(database_path=path)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c
    os.unlink(path)


def _create(client, **overrides):
    payload = {
        "title": "The Pragmatic Programmer",
        "author": "Andy Hunt",
        "year": 1999,
        "isbn": "978-0201616224",
    }
    payload.update(overrides)
    return client.post("/books", json=payload)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_book_success(client):
    resp = _create(client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] > 0
    assert body["title"] == "The Pragmatic Programmer"
    assert body["author"] == "Andy Hunt"
    assert body["year"] == 1999
    assert body["isbn"] == "978-0201616224"


def test_create_book_requires_title_and_author(client):
    resp = client.post("/books", json={"year": 2020})
    assert resp.status_code == 400
    errors = resp.get_json()["errors"]
    assert any("title" in e for e in errors)
    assert any("author" in e for e in errors)


def test_create_book_rejects_blank_strings(client):
    resp = client.post("/books", json={"title": "   ", "author": ""})
    assert resp.status_code == 400


def test_create_book_rejects_non_json(client):
    resp = client.post("/books", data="not json", content_type="text/plain")
    assert resp.status_code == 400


def test_create_book_rejects_bad_year_type(client):
    resp = client.post(
        "/books",
        json={"title": "X", "author": "Y", "year": "nineteen ninety"},
    )
    assert resp.status_code == 400


def test_list_books_empty(client):
    resp = client.get("/books")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_list_books_and_filter_by_author(client):
    _create(client, title="A", author="Alice")
    _create(client, title="B", author="Bob")
    _create(client, title="C", author="Alice")

    all_resp = client.get("/books")
    assert all_resp.status_code == 200
    assert len(all_resp.get_json()) == 3

    filtered = client.get("/books?author=Alice")
    assert filtered.status_code == 200
    titles = [b["title"] for b in filtered.get_json()]
    assert titles == ["A", "C"]

    none = client.get("/books?author=Zed")
    assert none.status_code == 200
    assert none.get_json() == []


def test_get_book_by_id(client):
    created = _create(client).get_json()
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json() == created


def test_get_book_not_found(client):
    resp = client.get("/books/9999")
    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_update_book_full(client):
    created = _create(client).get_json()
    resp = client.put(
        f"/books/{created['id']}",
        json={
            "title": "New Title",
            "author": "New Author",
            "year": 2020,
            "isbn": "111",
        },
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "New Title"
    assert body["author"] == "New Author"
    assert body["year"] == 2020
    assert body["isbn"] == "111"


def test_update_book_partial(client):
    created = _create(client).get_json()
    resp = client.put(f"/books/{created['id']}", json={"title": "Renamed"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "Renamed"
    assert body["author"] == created["author"]
    assert body["year"] == created["year"]


def test_update_book_invalid_field(client):
    created = _create(client).get_json()
    resp = client.put(f"/books/{created['id']}", json={"title": ""})
    assert resp.status_code == 400


def test_update_book_not_found(client):
    resp = client.put("/books/9999", json={"title": "x"})
    assert resp.status_code == 404


def test_update_book_empty_body(client):
    created = _create(client).get_json()
    resp = client.put(f"/books/{created['id']}", json={})
    assert resp.status_code == 400


def test_delete_book(client):
    created = _create(client).get_json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204
    assert resp.data == b""

    follow = client.get(f"/books/{created['id']}")
    assert follow.status_code == 404


def test_delete_book_not_found(client):
    resp = client.delete("/books/9999")
    assert resp.status_code == 404


def test_unknown_route_returns_json_404(client):
    resp = client.get("/nope")
    assert resp.status_code == 404
    assert resp.is_json
