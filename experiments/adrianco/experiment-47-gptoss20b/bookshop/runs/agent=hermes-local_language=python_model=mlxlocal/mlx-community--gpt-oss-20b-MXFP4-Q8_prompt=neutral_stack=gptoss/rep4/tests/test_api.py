import os
import shutil
import pytest
from starlette.testclient import TestClient
from main import app

# Use a fresh database for each test session
DB_FILE = "books.db"

@pytest.fixture(autouse=True, scope="module")
def clean_db(tmp_path_factory):
    # ensure test directory
    tmp_dir = tmp_path_factory.mktemp("data")
    os.chdir(tmp_dir)
    # ensure no preexisting db
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    yield
    # cleanup after tests
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

def test_create_and_get_book():
    payload = {"title": "Test Book", "author": "Author A", "year": 2021, "isbn": "123"}
    r = client.post("/books", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["id"] == 1
    assert data["title"] == payload["title"]

    r2 = client.get(f"/books/{data['id']}")
    assert r2.status_code == 200
    assert r2.json() == data

def test_update_book():
    # create
    payload = {"title": "Old Title", "author": "A"}
    r = client.post("/books", json=payload)
    book_id = r.json()["id"]
    # update
    update = {"title": "New Title"}
    r2 = client.put(f"/books/{book_id}", json=update)
    assert r2.status_code == 200
    assert r2.json()["title"] == "New Title"

def test_delete_book():
    payload = {"title": "Delete Me", "author": "B"}
    r = client.post("/books", json=payload)
    book_id = r.json()["id"]
    r2 = client.delete(f"/books/{book_id}")
    assert r2.status_code == 204
    # verify not found
    r3 = client.get(f"/books/{book_id}")
    assert r3.status_code == 404

def test_list_books_author_filter():
    # create two books with same author
    client.post("/books", json={"title": "B1", "author": "Same"})
    client.post("/books", json={"title": "B2", "author": "Same"})
    client.post("/books", json={"title": "B3", "author": "Other"})
    r = client.get("/books?author=Same")
    assert r.status_code == 200
    books = r.json()
    assert len(books) == 2
    assert all(book["author"] == "Same" for book in books)
