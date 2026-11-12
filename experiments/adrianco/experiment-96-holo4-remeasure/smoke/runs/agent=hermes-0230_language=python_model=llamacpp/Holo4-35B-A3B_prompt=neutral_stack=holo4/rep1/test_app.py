import os
import json
import pytest
from app import app, init_db

TEST_DB = "test_books.db"


@pytest.fixture(autouse=True)
def client():
    app.config["TESTING"] = True
    # Use an in-memory db for tests by patching get_db
    import app as app_module
    original_db = app_module.DATABASE
    app_module.DATABASE = TEST_DB
    init_db()
    yield app.test_client()
    app_module.DATABASE = original_db
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def test_health():
    resp = app.test_client().get("/health")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["status"] == "ok"


def test_create_book():
    resp = app.test_client().post(
        "/books",
        data=json.dumps({"title": "1984", "author": "George Orwell", "year": 1949}),
        content_type="application/json",
    )
    assert resp.status_code == 201
    data = json.loads(resp.data)
    assert data["title"] == "1984"
    assert data["author"] == "George Orwell"
    assert data["year"] == 1949
    assert "id" in data


def test_create_book_missing_title():
    resp = app.test_client().post(
        "/books",
        data=json.dumps({"author": "George Orwell"}),
        content_type="application/json",
    )
    assert resp.status_code == 400
    data = json.loads(resp.data)
    assert "error" in data


def test_create_book_missing_author():
    resp = app.test_client().post(
        "/books",
        data=json.dumps({"title": "1984"}),
        content_type="application/json",
    )
    assert resp.status_code == 400
    data = json.loads(resp.data)
    assert "error" in data


def test_list_books():
    # Create a couple of books first
    app.test_client().post(
        "/books",
        data=json.dumps({"title": "1984", "author": "George Orwell"}),
        content_type="application/json",
    )
    app.test_client().post(
        "/books",
        data=json.dumps({"title": "Animal Farm", "author": "George Orwell"}),
        content_type="application/json",
    )
    app.test_client().post(
        "/books",
        data=json.dumps({"title": "Brave New World", "author": "Aldous Huxley"}),
        content_type="application/json",
    )

    resp = app.test_client().get("/books")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data) == 3

    # Filter by author
    resp = app.test_client().get("/books?author=George Orwell")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data) == 2
    assert all(b["author"] == "George Orwell" for b in data)


def test_get_book():
    resp = app.test_client().post(
        "/books",
        data=json.dumps({"title": "1984", "author": "George Orwell"}),
        content_type="application/json",
    )
    book_id = json.loads(resp.data)["id"]
    resp = app.test_client().get(f"/books/{book_id}")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["title"] == "1984"


def test_get_book_not_found():
    resp = app.test_client().get("/books/9999")
    assert resp.status_code == 404


def test_update_book():
    resp = app.test_client().post(
        "/books",
        data=json.dumps({"title": "1984", "author": "George Orwell"}),
        content_type="application/json",
    )
    book_id = json.loads(resp.data)["id"]
    resp = app.test_client().put(
        f"/books/{book_id}",
        data=json.dumps({"title": "Nineteen Eighty-Four"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["title"] == "Nineteen Eighty-Four"
    assert data["author"] == "George Orwell"


def test_delete_book():
    resp = app.test_client().post(
        "/books",
        data=json.dumps({"title": "1984", "author": "George Orwell"}),
        content_type="application/json",
    )
    book_id = json.loads(resp.data)["id"]
    resp = app.test_client().delete(f"/books/{book_id}")
    assert resp.status_code == 204
    resp = app.test_client().get(f"/books/{book_id}")
    assert resp.status_code == 404
