import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(db_path=str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def make_book(client, **overrides):
    data = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}
    data.update(overrides)
    return client.post("/books", json=data)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_book(client):
    resp = make_book(client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] == 1
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"
    assert body["year"] == 1965


def test_create_requires_title_and_author(client):
    resp = client.post("/books", json={"year": 2000})
    assert resp.status_code == 400
    errors = resp.get_json()["errors"]
    assert any("title" in e for e in errors)
    assert any("author" in e for e in errors)


def test_create_rejects_non_json(client):
    resp = client.post("/books", data="not json", content_type="text/plain")
    assert resp.status_code == 400


def test_list_and_filter_by_author(client):
    make_book(client)
    make_book(client, title="Hyperion", author="Dan Simmons")
    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 2

    resp = client.get("/books?author=Dan Simmons")
    books = resp.get_json()
    assert len(books) == 1
    assert books[0]["title"] == "Hyperion"


def test_get_single_book(client):
    book_id = make_book(client).get_json()["id"]
    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Dune"


def test_get_missing_book_404(client):
    assert client.get("/books/999").status_code == 404


def test_update_book(client):
    book_id = make_book(client).get_json()["id"]
    resp = client.put(f"/books/{book_id}", json={"title": "Dune Messiah", "year": 1969})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "Dune Messiah"
    assert body["year"] == 1969
    assert body["author"] == "Frank Herbert"


def test_update_validation(client):
    book_id = make_book(client).get_json()["id"]
    resp = client.put(f"/books/{book_id}", json={"title": ""})
    assert resp.status_code == 400


def test_update_missing_book_404(client):
    assert client.put("/books/999", json={"title": "X"}).status_code == 404


def test_delete_book(client):
    book_id = make_book(client).get_json()["id"]
    assert client.delete(f"/books/{book_id}").status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404


def test_delete_missing_book_404(client):
    assert client.delete("/books/999").status_code == 404
