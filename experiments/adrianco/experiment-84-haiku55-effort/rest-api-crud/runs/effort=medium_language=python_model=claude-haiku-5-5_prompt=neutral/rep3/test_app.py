import pytest

from app import create_app

VALID_BOOK = {
    "title": "Dune",
    "author": "Frank Herbert",
    "year": 1965,
    "isbn": "9780441013593",
}


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def create(client, **overrides):
    payload = {**VALID_BOOK, **overrides}
    return client.post("/books", json=payload)


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_and_get_book(client):
    resp = create(client)
    assert resp.status_code == 201
    book = resp.get_json()
    assert book["id"] >= 1
    assert book["title"] == "Dune"
    assert book["author"] == "Frank Herbert"
    assert book["year"] == 1965
    assert book["isbn"] == "9780441013593"
    assert resp.headers["Location"] == f"/books/{book['id']}"

    fetched = client.get(f"/books/{book['id']}")
    assert fetched.status_code == 200
    assert fetched.get_json() == book


def test_create_book_with_only_required_fields(client):
    resp = client.post("/books", json={"title": "Solaris", "author": "Stanisław Lem"})
    assert resp.status_code == 201
    book = resp.get_json()
    assert book["year"] is None
    assert book["isbn"] is None


def test_list_books_and_author_filter(client):
    create(client, title="Dune", author="Frank Herbert")
    create(client, title="Children of Dune", author="Frank Herbert")
    create(client, title="Solaris", author="Stanisław Lem")

    all_books = client.get("/books").get_json()
    assert [b["title"] for b in all_books] == ["Dune", "Children of Dune", "Solaris"]

    herbert = client.get("/books?author=Frank Herbert").get_json()
    assert [b["title"] for b in herbert] == ["Dune", "Children of Dune"]

    # Filter is case-insensitive.
    assert len(client.get("/books?author=frank herbert").get_json()) == 2

    assert client.get("/books?author=Nobody").get_json() == []


def test_list_empty_collection(client):
    resp = client.get("/books")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_get_missing_book_returns_404(client):
    resp = client.get("/books/999")
    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_update_book(client):
    book_id = create(client).get_json()["id"]

    resp = client.put(
        f"/books/{book_id}",
        json={"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969},
    )
    assert resp.status_code == 200
    updated = resp.get_json()
    assert updated["id"] == book_id
    assert updated["title"] == "Dune Messiah"
    assert updated["year"] == 1969
    assert updated["isbn"] is None  # PUT replaces the whole record

    assert client.get(f"/books/{book_id}").get_json() == updated


def test_update_missing_book_returns_404(client):
    resp = client.put("/books/42", json=VALID_BOOK)
    assert resp.status_code == 404


def test_update_validates_payload(client):
    book_id = create(client).get_json()["id"]
    resp = client.put(f"/books/{book_id}", json={"title": "", "author": "X"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["details"]


def test_delete_book(client):
    book_id = create(client).get_json()["id"]

    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 204
    assert resp.data == b""

    assert client.get(f"/books/{book_id}").status_code == 404
    assert client.delete(f"/books/{book_id}").status_code == 404


@pytest.mark.parametrize(
    "payload, field",
    [
        ({"author": "Frank Herbert"}, "title"),
        ({"title": "Dune"}, "author"),
        ({"title": "   ", "author": "Frank Herbert"}, "title"),
        ({"title": "Dune", "author": 123}, "author"),
        ({"title": "Dune", "author": "Frank Herbert", "year": "1965"}, "year"),
        ({"title": "Dune", "author": "Frank Herbert", "year": True}, "year"),
        ({"title": "Dune", "author": "Frank Herbert", "year": -5}, "year"),
        ({"title": "Dune", "author": "Frank Herbert", "isbn": 123}, "isbn"),
    ],
)
def test_create_rejects_invalid_payloads(client, payload, field):
    resp = client.post("/books", json=payload)
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["error"] == "validation failed"
    assert field in body["details"]


def test_create_rejects_non_json_body(client):
    resp = client.post("/books", data="not json", content_type="text/plain")
    assert resp.status_code == 400


def test_create_rejects_json_array(client):
    resp = client.post("/books", json=[VALID_BOOK])
    assert resp.status_code == 400
    assert "body" in resp.get_json()["details"]


def test_unknown_route_returns_json_404(client):
    resp = client.get("/nope")
    assert resp.status_code == 404
    assert resp.is_json


def test_wrong_method_returns_json_405(client):
    resp = client.patch("/health")
    assert resp.status_code == 405
    assert resp.is_json


def test_data_persists_across_app_instances(tmp_path):
    db_path = str(tmp_path / "persist.db")
    first = create_app(db_path)
    with first.test_client() as c:
        book_id = c.post("/books", json=VALID_BOOK).get_json()["id"]

    second = create_app(db_path)
    with second.test_client() as c:
        assert c.get(f"/books/{book_id}").get_json()["title"] == "Dune"
