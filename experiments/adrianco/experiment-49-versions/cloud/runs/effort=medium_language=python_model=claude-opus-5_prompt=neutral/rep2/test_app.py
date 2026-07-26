import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app(database=str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def make_book(client, **overrides):
    payload = {
        "title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "isbn": "9780441013593",
    }
    payload.update(overrides)
    resp = client.post("/books", json=payload)
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_book_returns_201_with_id(client):
    book = make_book(client)
    assert isinstance(book["id"], int)
    assert book["title"] == "Dune"
    assert book["author"] == "Frank Herbert"
    assert book["year"] == 1965
    assert book["isbn"] == "9780441013593"


def test_create_requires_title_and_author(client):
    resp = client.post("/books", json={"year": 1999})
    assert resp.status_code == 400
    details = resp.get_json()["details"]
    assert "title is required" in details
    assert "author is required" in details


@pytest.mark.parametrize(
    "payload, expected",
    [
        ({"title": "  ", "author": "A"}, "title must be a non-empty string"),
        ({"title": "T", "author": ""}, "author must be a non-empty string"),
        ({"title": "T", "author": "A", "year": "old"}, "year must be an integer"),
        ({"title": "T", "author": "A", "year": 9999}, "year must be between 0 and 2200"),
        ({"title": "T", "author": "A", "isbn": 123}, "isbn must be a string"),
    ],
)
def test_create_validation_errors(client, payload, expected):
    resp = client.post("/books", json=payload)
    assert resp.status_code == 400
    assert expected in resp.get_json()["details"]


def test_create_with_non_json_body(client):
    resp = client.post("/books", data="not json", content_type="text/plain")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation failed"


def test_list_books_and_author_filter(client):
    make_book(client)
    make_book(client, title="Emma", author="Jane Austen", year=1815, isbn=None)

    all_books = client.get("/books").get_json()
    assert [b["title"] for b in all_books] == ["Dune", "Emma"]

    filtered = client.get("/books?author=Jane Austen").get_json()
    assert len(filtered) == 1
    assert filtered[0]["title"] == "Emma"
    assert filtered[0]["isbn"] is None

    assert client.get("/books?author=Nobody").get_json() == []


def test_get_single_book(client):
    book = make_book(client)
    resp = client.get(f"/books/{book['id']}")
    assert resp.status_code == 200
    assert resp.get_json() == book


def test_get_missing_book_returns_404(client):
    resp = client.get("/books/424242")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "book not found"


def test_update_book(client):
    book = make_book(client)
    resp = client.put(
        f"/books/{book['id']}",
        json={"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969},
    )
    assert resp.status_code == 200
    updated = resp.get_json()
    assert updated["title"] == "Dune Messiah"
    assert updated["year"] == 1969
    # Persisted, not just echoed back.
    assert client.get(f"/books/{book['id']}").get_json() == updated


def test_partial_update_leaves_other_fields_intact(client):
    book = make_book(client)
    resp = client.put(f"/books/{book['id']}", json={"year": 1966})
    assert resp.status_code == 200
    assert resp.get_json() == {**book, "year": 1966}


def test_update_rejects_invalid_and_empty_payloads(client):
    book = make_book(client)
    assert client.put(f"/books/{book['id']}", json={"title": ""}).status_code == 400
    assert client.put(f"/books/{book['id']}", json={}).status_code == 400
    # Unchanged after failed updates.
    assert client.get(f"/books/{book['id']}").get_json() == book


def test_update_missing_book_returns_404(client):
    resp = client.put("/books/424242", json={"title": "X", "author": "Y"})
    assert resp.status_code == 404


def test_delete_book(client):
    book = make_book(client)
    resp = client.delete(f"/books/{book['id']}")
    assert resp.status_code == 204
    assert resp.data == b""
    assert client.get(f"/books/{book['id']}").status_code == 404
    assert client.delete(f"/books/{book['id']}").status_code == 404


def test_data_persists_across_app_instances(tmp_path):
    path = str(tmp_path / "persist.db")
    with create_app(database=path).test_client() as client:
        book = make_book(client)
    with create_app(database=path).test_client() as client:
        assert client.get(f"/books/{book['id']}").get_json() == book


def test_unknown_route_returns_json_404(client):
    resp = client.get("/nope")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "not found"}
