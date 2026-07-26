import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(db_path=str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def make_book(client, **overrides):
    payload = {"title": "Release It!", "author": "Michael Nygard", "year": 2018, "isbn": "978-1680502398"}
    payload.update(overrides)
    return client.post("/books", json=payload)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_book_returns_201_with_body(client):
    resp = make_book(client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] == 1
    assert body["title"] == "Release It!"
    assert body["author"] == "Michael Nygard"
    assert body["year"] == 2018
    assert body["isbn"] == "978-1680502398"


def test_create_book_optional_fields_default_to_null(client):
    resp = client.post("/books", json={"title": "Sun Performance", "author": "Adrian Cockcroft"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["year"] is None
    assert body["isbn"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": "No author"},
        {"author": "No title"},
        {"title": "", "author": "Someone"},
        {"title": "   ", "author": "Someone"},
        {"title": 42, "author": "Someone"},
        {"title": "Ok", "author": "Ok", "year": "1999"},
    ],
)
def test_create_book_validation_errors(client, payload):
    resp = client.post("/books", json=payload)
    assert resp.status_code == 400
    assert "errors" in resp.get_json()


def test_create_book_rejects_non_json_body(client):
    resp = client.post("/books", data="not json", content_type="text/plain")
    assert resp.status_code == 400


def test_list_books(client):
    make_book(client)
    make_book(client, title="Migrating to Cloud Native", author="Adrian Cockcroft")
    resp = client.get("/books")
    assert resp.status_code == 200
    books = resp.get_json()
    assert len(books) == 2
    assert [b["id"] for b in books] == [1, 2]


def test_list_books_author_filter(client):
    make_book(client)
    make_book(client, title="Cloud Book", author="Adrian Cockcroft")
    resp = client.get("/books?author=Adrian Cockcroft")
    assert resp.status_code == 200
    books = resp.get_json()
    assert len(books) == 1
    assert books[0]["title"] == "Cloud Book"

    resp = client.get("/books?author=Nobody")
    assert resp.get_json() == []


def test_get_book_by_id(client):
    make_book(client)
    resp = client.get("/books/1")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Release It!"


def test_get_missing_book_returns_404(client):
    resp = client.get("/books/999")
    assert resp.status_code == 404


def test_update_book(client):
    make_book(client)
    resp = client.put("/books/1", json={"title": "Release It! 2nd Ed", "year": 2018})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "Release It! 2nd Ed"
    assert body["author"] == "Michael Nygard"

    # persisted
    assert client.get("/books/1").get_json()["title"] == "Release It! 2nd Ed"


def test_update_book_validation_and_missing(client):
    make_book(client)
    assert client.put("/books/1", json={"title": ""}).status_code == 400
    assert client.put("/books/1", json={}).status_code == 400
    assert client.put("/books/999", json={"title": "X"}).status_code == 404


def test_delete_book(client):
    make_book(client)
    resp = client.delete("/books/1")
    assert resp.status_code == 204
    assert client.get("/books/1").status_code == 404
    assert client.delete("/books/1").status_code == 404
