import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

# Helper to reset DB
import os
import sqlite3

def reset_db():
    if os.path.exists("books.db"):
        os.remove("books.db")
    # Recreate tables
    from app import Base, engine
    Base.metadata.create_all(engine)

@pytest.fixture(autouse=True)
def setup():
    reset_db()

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

def test_create_and_get_book():
    payload = {"title": "Test Book", "author": "Author", "year": 2021, "isbn": "123"}
    r = client.post("/books", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == payload["title"]
    book_id = data["id"]
    r2 = client.get(f"/books/{book_id}")
    assert r2.status_code == 200
    assert r2.json()["author"] == payload["author"]

def test_list_filter_author():
    client.post("/books", json={"title": "A", "author": "X"})
    client.post("/books", json={"title": "B", "author": "Y"})
    r = client.get("/books?author=Y")
    assert r.status_code == 200
    books = r.json()
    assert len(books) == 1
    assert books[0]["author"] == "Y"

def test_update_book():
    r = client.post("/books", json={"title": "Old", "author": "A"})
    book_id = r.json()["id"]
    r2 = client.put(f"/books/{book_id}", json={"title": "New", "author": "A"})
    assert r2.status_code == 200
    assert r2.json()["title"] == "New"

def test_delete_book():
    r = client.post("/books", json={"title": "ToDelete", "author": "A"})
    book_id = r.json()["id"]
    r2 = client.delete(f"/books/{book_id}")
    assert r2.status_code == 204
    r3 = client.get(f"/books/{book_id}")
    assert r3.status_code == 404
