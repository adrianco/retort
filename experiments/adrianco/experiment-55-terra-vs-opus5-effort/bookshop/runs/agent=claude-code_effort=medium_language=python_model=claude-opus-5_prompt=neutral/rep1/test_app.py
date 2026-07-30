"""Integration tests for the books API, driven through Flask's test client."""

import pytest

from app import create_app, validate_book, ValidationError


@pytest.fixture
def client(tmp_path):
    app = create_app(database=str(tmp_path / "test_books.db"))
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


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


# --- health -------------------------------------------------------------


def test_health_reports_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok", "database": "ok"}


# --- create -------------------------------------------------------------


def test_create_book_returns_201_with_id_and_location(client):
    resp = client.post(
        "/books",
        json={"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978"},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert isinstance(body["id"], int)
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"
    assert body["year"] == 1965
    assert body["isbn"] == "978"
    assert resp.headers["Location"] == f"/books/{body['id']}"
    assert resp.mimetype == "application/json"


def test_create_book_allows_optional_fields_to_be_omitted(client):
    body = make_book(client, title="Untitled Draft")
    resp = client.post("/books", json={"title": "Minimal", "author": "Nobody"})
    assert resp.status_code == 201
    assert resp.get_json()["year"] is None
    assert resp.get_json()["isbn"] is None
    assert body["id"] != resp.get_json()["id"]


@pytest.mark.parametrize(
    "payload,bad_field",
    [
        ({"author": "Frank Herbert"}, "title"),
        ({"title": "Dune"}, "author"),
        ({"title": "   ", "author": "Frank Herbert"}, "title"),
        ({"title": "Dune", "author": ""}, "author"),
        ({"title": "Dune", "author": 42}, "author"),
        ({"title": "Dune", "author": "FH", "year": "nineteen"}, "year"),
        ({"title": "Dune", "author": "FH", "year": 9999}, "year"),
    ],
)
def test_create_book_rejects_invalid_input(client, payload, bad_field):
    resp = client.post("/books", json=payload)
    assert resp.status_code == 400
    assert bad_field in resp.get_json()["details"]
    # Nothing was persisted.
    assert client.get("/books").get_json() == []


def test_create_book_rejects_missing_or_malformed_body(client):
    assert client.post("/books").status_code == 400
    assert client.post(
        "/books", data="not json", content_type="application/json"
    ).status_code == 400
    assert client.post("/books", json=["a", "list"]).status_code == 400


def test_create_book_trims_whitespace(client):
    book = make_book(client, title="  Dune  ", author="  Frank Herbert ")
    assert book["title"] == "Dune"
    assert book["author"] == "Frank Herbert"


# --- list ---------------------------------------------------------------


def test_list_books_returns_all_books_in_id_order(client):
    a = make_book(client, title="Dune")
    b = make_book(client, title="Neuromancer", author="William Gibson")
    resp = client.get("/books")
    assert resp.status_code == 200
    assert [x["id"] for x in resp.get_json()] == [a["id"], b["id"]]


def test_list_books_filters_by_author(client):
    make_book(client, title="Dune", author="Frank Herbert")
    make_book(client, title="Dune Messiah", author="Frank Herbert")
    make_book(client, title="Neuromancer", author="William Gibson")

    resp = client.get("/books?author=Frank Herbert")
    assert resp.status_code == 200
    titles = sorted(b["title"] for b in resp.get_json())
    assert titles == ["Dune", "Dune Messiah"]

    # Filter is case-insensitive, and an unmatched author yields an empty list.
    assert len(client.get("/books?author=frank herbert").get_json()) == 2
    assert client.get("/books?author=Nobody").get_json() == []


# --- get by id ----------------------------------------------------------


def test_get_book_by_id(client):
    created = make_book(client)
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json() == created


def test_get_missing_book_returns_404(client):
    resp = client.get("/books/999")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Not Found"


# --- update -------------------------------------------------------------


def test_update_book_replaces_fields(client):
    created = make_book(client)
    resp = client.put(
        f"/books/{created['id']}",
        json={"title": "Dune (Revised)", "author": "Frank Herbert", "year": 1984},
    )
    assert resp.status_code == 200
    updated = resp.get_json()
    assert updated["id"] == created["id"]
    assert updated["title"] == "Dune (Revised)"
    assert updated["year"] == 1984
    assert updated["isbn"] is None  # PUT replaces the whole resource
    assert client.get(f"/books/{created['id']}").get_json() == updated


def test_update_validates_input_and_leaves_record_untouched(client):
    created = make_book(client)
    resp = client.put(f"/books/{created['id']}", json={"title": "No Author"})
    assert resp.status_code == 400
    assert "author" in resp.get_json()["details"]
    assert client.get(f"/books/{created['id']}").get_json() == created


def test_update_missing_book_returns_404(client):
    resp = client.put("/books/999", json={"title": "Ghost", "author": "Nobody"})
    assert resp.status_code == 404


# --- delete -------------------------------------------------------------


def test_delete_book_returns_204_and_removes_it(client):
    created = make_book(client)
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204
    assert resp.get_data() == b""
    assert client.get(f"/books/{created['id']}").status_code == 404
    assert client.get("/books").get_json() == []


def test_delete_is_not_idempotent_in_status(client):
    created = make_book(client)
    assert client.delete(f"/books/{created['id']}").status_code == 204
    assert client.delete(f"/books/{created['id']}").status_code == 404


# --- misc ---------------------------------------------------------------


def test_unknown_route_and_method_return_json_errors(client):
    resp = client.get("/nope")
    assert resp.status_code == 404
    assert resp.mimetype == "application/json"

    resp = client.patch("/books/1", json={})
    assert resp.status_code == 405
    assert resp.mimetype == "application/json"


def test_data_persists_across_app_instances(tmp_path):
    db = str(tmp_path / "persist.db")
    with create_app(database=db).test_client() as c:
        c.post("/books", json={"title": "Dune", "author": "Frank Herbert"})
    with create_app(database=db).test_client() as c:
        assert [b["title"] for b in c.get("/books").get_json()] == ["Dune"]


# --- validator unit tests ----------------------------------------------


def test_validate_book_partial_allows_missing_required_fields():
    assert validate_book({"year": 2001}, partial=True) == {"year": 2001}


def test_validate_book_rejects_unknown_fields():
    with pytest.raises(ValidationError) as exc:
        validate_book({"title": "T", "author": "A", "publisher": "X"})
    assert "publisher" in exc.value.errors["_unknown"]
