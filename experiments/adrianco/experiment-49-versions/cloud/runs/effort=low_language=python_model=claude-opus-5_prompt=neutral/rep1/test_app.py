import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BOOKS_DB", str(tmp_path / "test.db"))
    import app as app_module

    with TestClient(app_module.app) as c:
        yield c


SAMPLE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_and_get(client):
    r = client.post("/books", json=SAMPLE)
    assert r.status_code == 201
    created = r.json()
    assert created["id"] > 0
    assert created["title"] == "Dune"

    r = client.get(f"/books/{created['id']}")
    assert r.status_code == 200
    assert r.json() == created


def test_validation_requires_title_and_author(client):
    assert client.post("/books", json={"author": "X"}).status_code == 422
    assert client.post("/books", json={"title": "X"}).status_code == 422
    assert client.post("/books", json={"title": "  ", "author": "X"}).status_code == 422
    assert client.post("/books", json={"title": "X", "author": "Y", "year": 9999}).status_code == 422


def test_list_and_author_filter(client):
    client.post("/books", json=SAMPLE)
    client.post("/books", json={"title": "Neuromancer", "author": "William Gibson"})

    assert len(client.get("/books").json()) == 2

    filtered = client.get("/books", params={"author": "William Gibson"}).json()
    assert [b["title"] for b in filtered] == ["Neuromancer"]

    assert client.get("/books", params={"author": "Nobody"}).json() == []


def test_update(client):
    book_id = client.post("/books", json=SAMPLE).json()["id"]
    r = client.put(f"/books/{book_id}", json={**SAMPLE, "title": "Dune Messiah", "year": 1969})
    assert r.status_code == 200
    assert r.json()["title"] == "Dune Messiah"
    assert client.get(f"/books/{book_id}").json()["year"] == 1969


def test_delete(client):
    book_id = client.post("/books", json=SAMPLE).json()["id"]
    assert client.delete(f"/books/{book_id}").status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404
    assert client.delete(f"/books/{book_id}").status_code == 404


def test_missing_ids_404(client):
    assert client.get("/books/999").status_code == 404
    assert client.put("/books/999", json=SAMPLE).status_code == 404


def test_data_persists_in_sqlite_file(client, tmp_path):
    client.post("/books", json=SAMPLE)
    assert os.path.exists(os.environ["BOOKS_DB"])

    import sqlite3

    with sqlite3.connect(os.environ["BOOKS_DB"]) as conn:
        assert conn.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 1
