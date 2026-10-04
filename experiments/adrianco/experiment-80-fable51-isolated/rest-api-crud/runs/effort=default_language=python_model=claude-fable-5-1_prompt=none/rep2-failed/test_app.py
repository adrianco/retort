import pytest

from app import create_app

BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    return app.test_client()


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_and_get_book(client):
    resp = client.post("/books", json=BOOK)
    assert resp.status_code == 201
    created = resp.get_json()
    assert created == {"id": created["id"], **BOOK}
    assert resp.headers["Location"] == f"/books/{created['id']}"

    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json() == created


def test_create_with_only_required_fields(client):
    resp = client.post("/books", json={"title": "T", "author": "A"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["year"] is None and body["isbn"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {"author": "A"},
        {"title": "T"},
        {"title": "  ", "author": "A"},
        {"title": "T", "author": 5},
        {"title": "T", "author": "A", "year": "1965"},
        {"title": "T", "author": "A", "year": True},
        {"title": "T", "author": "A", "isbn": 123},
        ["not", "an", "object"],
    ],
)
def test_create_validation_errors(client, payload):
    resp = client.post("/books", json=payload)
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["error"] == "validation failed"
    assert body["details"]


def test_create_rejects_malformed_json(client):
    resp = client.post("/books", data="{nope", content_type="application/json")
    assert resp.status_code == 400


def test_duplicate_isbn_conflict(client):
    assert client.post("/books", json=BOOK).status_code == 201
    assert client.post("/books", json=BOOK).status_code == 409


def test_list_books_and_author_filter(client):
    client.post("/books", json=BOOK)
    client.post("/books", json={"title": "Emma", "author": "Jane Austen", "year": 1815})
    client.post("/books", json={"title": "Persuasion", "author": "Jane Austen"})

    resp = client.get("/books")
    assert resp.status_code == 200
    assert [b["title"] for b in resp.get_json()] == ["Dune", "Emma", "Persuasion"]

    resp = client.get("/books?author=Jane Austen")
    assert [b["title"] for b in resp.get_json()] == ["Emma", "Persuasion"]

    assert client.get("/books?author=Nobody").get_json() == []


def test_update_book(client):
    book_id = client.post("/books", json=BOOK).get_json()["id"]

    resp = client.put(f"/books/{book_id}", json={**BOOK, "title": "Dune Messiah", "year": 1969})
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Dune Messiah"
    assert client.get(f"/books/{book_id}").get_json()["year"] == 1969

    assert client.put(f"/books/{book_id}", json={"title": "No author"}).status_code == 400
    assert client.put("/books/9999", json=BOOK).status_code == 404


def test_delete_book(client):
    book_id = client.post("/books", json=BOOK).get_json()["id"]

    assert client.delete(f"/books/{book_id}").status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404
    assert client.delete(f"/books/{book_id}").status_code == 404


def test_not_found_is_json(client):
    resp = client.get("/books/12345")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "book not found"}

    resp = client.get("/nope")
    assert resp.status_code == 404
    assert "error" in resp.get_json()
