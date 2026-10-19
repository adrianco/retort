"""Integration tests for the book collection REST API."""

import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app(db_path=str(tmp_path / "test_books.db"))
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def make_book(client, **overrides):
    payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965,
               "isbn": "9780441172719"}
    payload.update(overrides)
    return client.post("/books", json=payload)


# ------------------------------------------------------------------- health

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


# -------------------------------------------------------------------- create

def test_create_book_returns_201_with_id(client):
    resp = make_book(client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] == 1
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"
    assert body["year"] == 1965
    assert body["isbn"] == "9780441172719"


def test_create_book_optional_fields_omitted(client):
    resp = client.post("/books", json={"title": "1984", "author": "Orwell"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["year"] is None
    assert body["isbn"] is None


def test_create_book_missing_title_is_400(client):
    resp = client.post("/books", json={"author": "Frank Herbert"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"]


def test_create_book_missing_author_is_400(client):
    resp = client.post("/books", json={"title": "Dune"})
    assert resp.status_code == 400
    assert "author" in resp.get_json()["error"]


def test_create_book_blank_title_is_400(client):
    resp = client.post("/books", json={"title": "   ", "author": "X"})
    assert resp.status_code == 400


def test_create_book_invalid_year_is_400(client):
    resp = client.post("/books", json={"title": "Dune", "author": "FH",
                                       "year": "nineteen"})
    assert resp.status_code == 400
    assert "year" in resp.get_json()["error"]


def test_create_book_non_json_body_is_400(client):
    resp = client.post("/books", data="not json",
                       content_type="text/plain")
    assert resp.status_code == 400


# ---------------------------------------------------------------------- list

def test_list_books_empty(client):
    resp = client.get("/books")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_list_books_returns_all(client):
    make_book(client)
    make_book(client, title="Neuromancer", author="William Gibson",
              year=1984, isbn="9780441569595")
    resp = client.get("/books")
    assert resp.status_code == 200
    assert [b["title"] for b in resp.get_json()] == ["Dune", "Neuromancer"]


def test_list_books_filter_by_author(client):
    make_book(client)
    make_book(client, title="Hyperion", author="Dan Simmons", year=1989)
    resp = client.get("/books?author=Dan Simmons")
    assert resp.status_code == 200
    books = resp.get_json()
    assert len(books) == 1
    assert books[0]["title"] == "Hyperion"


def test_list_books_filter_no_match(client):
    make_book(client)
    resp = client.get("/books?author=Unknown")
    assert resp.status_code == 200
    assert resp.get_json() == []


# ----------------------------------------------------------------------- get

def test_get_book(client):
    created = make_book(client).get_json()
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json() == created


def test_get_book_not_found(client):
    resp = client.get("/books/999")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Book not found"


def test_get_book_non_integer_id_is_404(client):
    resp = client.get("/books/abc")
    assert resp.status_code == 404


# --------------------------------------------------------------------- update

def test_update_book_partial(client):
    created = make_book(client).get_json()
    resp = client.put(f"/books/{created['id']}",
                      json={"year": 1966, "isbn": "9780441172711"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["year"] == 1966
    assert body["isbn"] == "9780441172711"
    # untouched fields preserved
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"


def test_update_book_all_fields(client):
    created = make_book(client).get_json()
    resp = client.put(f"/books/{created['id']}",
                      json={"title": "Dune Messiah", "author": "Frank Herbert",
                            "year": 1969, "isbn": "9780441071607"})
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Dune Messiah"


def test_update_book_clears_optional_fields(client):
    created = make_book(client).get_json()
    resp = client.put(f"/books/{created['id']}", json={"year": None, "isbn": None})
    assert resp.status_code == 200
    assert resp.get_json()["year"] is None
    assert resp.get_json()["isbn"] is None


def test_update_book_not_found(client):
    resp = client.put("/books/999", json={"title": "Ghost"})
    assert resp.status_code == 404


def test_update_book_empty_body_is_400(client):
    created = make_book(client).get_json()
    resp = client.put(f"/books/{created['id']}", json={})
    assert resp.status_code == 400


def test_update_book_invalid_field_is_400(client):
    created = make_book(client).get_json()
    resp = client.put(f"/books/{created['id']}", json={"title": "  "})
    assert resp.status_code == 400


def test_update_book_unknown_field_is_400(client):
    created = make_book(client).get_json()
    resp = client.put(f"/books/{created['id']}", json={"genre": "sci-fi"})
    assert resp.status_code == 400
    assert "genre" in resp.get_json()["error"]


# -------------------------------------------------------------------- delete

def test_delete_book(client):
    created = make_book(client).get_json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204
    assert client.get(f"/books/{created['id']}").status_code == 404


def test_delete_book_not_found(client):
    resp = client.delete("/books/999")
    assert resp.status_code == 404


# ------------------------------------------------------------------ misc/http

def test_unknown_route_returns_json_404(client):
    resp = client.get("/nope")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Not found"


def test_wrong_method_returns_json_405(client):
    resp = client.patch("/books")
    assert resp.status_code == 405
    assert resp.get_json()["error"] == "Method not allowed"


def test_data_persists_across_requests(client):
    """A book created in one request is visible in later requests (SQLite)."""
    created = make_book(client).get_json()
    assert client.get(f"/books/{created['id']}").status_code == 200
