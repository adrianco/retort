import json
from flask.testing import FlaskClient
from main import app

client = app.test_client()

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok"}

# Test book creation, get, list, update, delete

def test_crud_book():
    # create
    payload = {"title": "Test Book", "author": "John Doe", "year": 2021, "isbn": "12345"}
    r = client.post("/books", json=payload)
    assert r.status_code == 201
    data = r.get_json()
    assert "id" in data and data["title"] == payload["title"]
    book_id = data["id"]

    # get single
    r = client.get(f"/books/{book_id}")
    assert r.status_code == 200
    assert r.get_json()["author"] == payload["author"]

    # list with filter
    r = client.get("/books", query_string={"author": "John Doe"})
    assert r.status_code == 200
    books = r.get_json()
    assert any(b["id"] == book_id for b in books)

    # update
    update_payload = {"title": "Updated Title"}
    r = client.put(f"/books/{book_id}", json=update_payload)
    assert r.status_code == 200
    assert r.get_json()["title"] == "Updated Title"

    # delete
    r = client.delete(f"/books/{book_id}")
    assert r.status_code == 204

    # verify deletion
    r = client.get(f"/books/{book_id}")
    assert r.status_code == 404
