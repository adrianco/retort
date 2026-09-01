import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok"}


def test_create_and_get_book(client):
    r = client.post("/books", json=BOOK)
    assert r.status_code == 201
    body = r.get_json()
    assert body["id"] == 1
    assert body["title"] == "Dune"
    r = client.get("/books/1")
    assert r.status_code == 200
    assert r.get_json() == body


def test_validation_errors(client):
    r = client.post("/books", json={"year": 2000})
    assert r.status_code == 400
    errors = r.get_json()["errors"]
    assert any("title" in e for e in errors)
    assert any("author" in e for e in errors)
    r = client.post("/books", json={"title": "X", "author": "Y", "year": "nope"})
    assert r.status_code == 400
    r = client.post("/books", data="not json", content_type="text/plain")
    assert r.status_code == 400


def test_list_and_filter_by_author(client):
    client.post("/books", json=BOOK)
    client.post("/books", json={"title": "Emma", "author": "Jane Austen"})
    client.post("/books", json={"title": "Persuasion", "author": "Jane Austen"})
    assert len(client.get("/books").get_json()) == 3
    filtered = client.get("/books?author=Jane Austen").get_json()
    assert [b["title"] for b in filtered] == ["Emma", "Persuasion"]
    assert client.get("/books?author=Nobody").get_json() == []


def test_update_book(client):
    client.post("/books", json=BOOK)
    r = client.put("/books/1", json={"year": 1966, "isbn": None})
    assert r.status_code == 200
    body = r.get_json()
    assert body["year"] == 1966 and body["isbn"] is None and body["title"] == "Dune"
    assert client.put("/books/1", json={"title": ""}).status_code == 400
    assert client.put("/books/1", json={}).status_code == 400
    assert client.put("/books/99", json={"title": "Z"}).status_code == 404


def test_delete_book(client):
    client.post("/books", json=BOOK)
    assert client.delete("/books/1").status_code == 204
    assert client.get("/books/1").status_code == 404
    assert client.delete("/books/1").status_code == 404
