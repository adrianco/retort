import pytest
from fastapi.testclient import TestClient

import db
import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    with TestClient(main.app) as c:
        yield c


def make(client, **kw):
    payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
    payload.update(kw)
    return client.post("/books", json=payload)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_and_get(client):
    r = make(client)
    assert r.status_code == 201
    book = r.json()
    assert book["id"] > 0
    assert book["title"] == "Dune"

    r = client.get(f"/books/{book['id']}")
    assert r.status_code == 200
    assert r.json() == book


def test_list_and_author_filter(client):
    make(client)
    make(client, title="Neuromancer", author="William Gibson", year=1984, isbn=None)

    assert len(client.get("/books").json()) == 2

    r = client.get("/books", params={"author": "William Gibson"})
    assert r.status_code == 200
    assert [b["title"] for b in r.json()] == ["Neuromancer"]

    assert client.get("/books", params={"author": "Nobody"}).json() == []


def test_update(client):
    book_id = make(client).json()["id"]
    r = client.put(
        f"/books/{book_id}",
        json={"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969, "isbn": None},
    )
    assert r.status_code == 200
    assert r.json()["title"] == "Dune Messiah"
    assert r.json()["isbn"] is None
    assert client.get(f"/books/{book_id}").json()["year"] == 1969


def test_delete(client):
    book_id = make(client).json()["id"]
    assert client.delete(f"/books/{book_id}").status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404
    assert client.delete(f"/books/{book_id}").status_code == 404


def test_missing_book_returns_404(client):
    assert client.get("/books/999").status_code == 404
    assert client.put("/books/999", json={"title": "x", "author": "y"}).status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"author": "Frank Herbert"},
        {"title": "Dune"},
        {"title": "", "author": "Frank Herbert"},
        {"title": "   ", "author": "Frank Herbert"},
        {"title": "Dune", "author": "Frank Herbert", "year": "not-a-year"},
    ],
)
def test_validation_errors(client, payload):
    assert client.post("/books", json=payload).status_code == 422
