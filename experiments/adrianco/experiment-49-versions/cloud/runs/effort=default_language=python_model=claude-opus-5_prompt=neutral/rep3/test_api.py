"""Integration tests for the book collection API.

Each test drives the real Flask app against a temporary SQLite database.
"""

import pytest


def post_book(client, **overrides):
    payload = {
        "title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "isbn": "9780441013593",
    }
    payload.update(overrides)
    return client.post("/books", json=payload)


# --------------------------------------------------------------------- health


def test_health_reports_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}


# --------------------------------------------------------------------- create


def test_create_book_returns_201_and_persists(client, sample_book):
    response = client.post("/books", json=sample_book)

    assert response.status_code == 201
    body = response.get_json()
    assert body["id"] > 0
    assert body["title"] == sample_book["title"]
    assert body["author"] == sample_book["author"]
    assert body["year"] == 1999
    assert body["isbn"] == "9780201616224"  # hyphens normalised away
    assert response.headers["Location"] == f"/books/{body['id']}"

    # The book survives into a separate request, i.e. it really hit SQLite.
    stored = client.get(f"/books/{body['id']}")
    assert stored.status_code == 200
    assert stored.get_json() == body


def test_create_book_accepts_only_required_fields(client):
    response = client.post("/books", json={"title": "Untitled", "author": "Anon"})

    assert response.status_code == 201
    body = response.get_json()
    assert body["year"] is None
    assert body["isbn"] is None


def test_create_book_trims_surrounding_whitespace(client):
    response = client.post("/books", json={"title": "  Dune  ", "author": "\tHerbert\n"})

    assert response.status_code == 201
    assert response.get_json()["title"] == "Dune"
    assert response.get_json()["author"] == "Herbert"


@pytest.mark.parametrize(
    "payload,bad_field",
    [
        ({"author": "Frank Herbert"}, "title"),
        ({"title": "Dune"}, "author"),
        ({"title": "   ", "author": "Frank Herbert"}, "title"),
        ({"title": "Dune", "author": ""}, "author"),
        ({"title": 42, "author": "Frank Herbert"}, "title"),
        ({"title": "Dune", "author": "Frank Herbert", "year": "1965"}, "year"),
        ({"title": "Dune", "author": "Frank Herbert", "year": 12}, "year"),
        ({"title": "Dune", "author": "Frank Herbert", "year": 9999}, "year"),
        ({"title": "Dune", "author": "Frank Herbert", "isbn": "nope"}, "isbn"),
    ],
)
def test_create_book_rejects_invalid_input(client, payload, bad_field):
    response = client.post("/books", json=payload)

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "Validation failed"
    assert bad_field in body["details"]

    assert client.get("/books").get_json() == []


def test_create_book_rejects_non_json_body(client):
    response = client.post("/books", data="title=Dune", content_type="text/plain")

    assert response.status_code == 400
    assert "body" in response.get_json()["details"]


def test_create_book_rejects_duplicate_isbn(client, sample_book):
    assert client.post("/books", json=sample_book).status_code == 201

    duplicate = dict(sample_book, title="Reprint")
    response = client.post("/books", json=duplicate)

    assert response.status_code == 409
    assert "already exists" in response.get_json()["error"]
    assert len(client.get("/books").get_json()) == 1


# ----------------------------------------------------------------------- list


def test_list_books_returns_all_books_in_insertion_order(client):
    post_book(client, title="Dune", isbn=None)
    post_book(client, title="Neuromancer", author="William Gibson", isbn=None)

    response = client.get("/books")

    assert response.status_code == 200
    titles = [book["title"] for book in response.get_json()]
    assert titles == ["Dune", "Neuromancer"]


def test_list_books_is_empty_initially(client):
    response = client.get("/books")

    assert response.status_code == 200
    assert response.get_json() == []


def test_list_books_filters_by_author_case_insensitively(client):
    post_book(client, title="Dune", author="Frank Herbert", isbn=None)
    post_book(client, title="Dune Messiah", author="Frank Herbert", isbn=None)
    post_book(client, title="Neuromancer", author="William Gibson", isbn=None)

    response = client.get("/books?author=frank herbert")

    assert response.status_code == 200
    books = response.get_json()
    assert [b["title"] for b in books] == ["Dune", "Dune Messiah"]


def test_list_books_author_filter_with_no_match_returns_empty_list(client):
    post_book(client, isbn=None)

    response = client.get("/books?author=Nobody")

    assert response.status_code == 200
    assert response.get_json() == []


def test_list_books_ignores_blank_author_filter(client):
    post_book(client, isbn=None)

    response = client.get("/books?author=")

    assert len(response.get_json()) == 1


# ------------------------------------------------------------------ retrieve


def test_get_missing_book_returns_404(client):
    response = client.get("/books/424242")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Book 424242 not found"


def test_get_book_with_non_integer_id_returns_404(client):
    assert client.get("/books/abc").status_code == 404


# -------------------------------------------------------------------- update


def test_update_book_replaces_fields_and_returns_200(client, sample_book):
    book_id = client.post("/books", json=sample_book).get_json()["id"]

    response = client.put(
        f"/books/{book_id}",
        json={"title": "The Pragmatic Programmer, 2nd Edition",
              "author": "Hunt & Thomas",
              "year": 2019},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["id"] == book_id
    assert body["title"] == "The Pragmatic Programmer, 2nd Edition"
    assert body["author"] == "Hunt & Thomas"
    assert body["year"] == 2019
    assert body["isbn"] is None  # PUT replaces the whole resource

    assert client.get(f"/books/{book_id}").get_json() == body


def test_update_missing_book_returns_404(client):
    response = client.put("/books/999", json={"title": "Ghost", "author": "Nobody"})

    assert response.status_code == 404
    assert response.get_json()["error"] == "Book 999 not found"


def test_update_book_validates_input(client, sample_book):
    book_id = client.post("/books", json=sample_book).get_json()["id"]

    response = client.put(f"/books/{book_id}", json={"author": "Hunt"})

    assert response.status_code == 400
    assert "title" in response.get_json()["details"]
    # The stored book is untouched.
    assert client.get(f"/books/{book_id}").get_json()["title"] == sample_book["title"]


def test_update_book_rejects_isbn_owned_by_another_book(client):
    first = post_book(client, title="Dune", isbn="9780441013593").get_json()
    second = post_book(client, title="Neuromancer", isbn="9780441569595").get_json()
    assert first["id"] != second["id"]

    response = client.put(
        f"/books/{second['id']}",
        json={"title": "Neuromancer", "author": "William Gibson",
              "isbn": "9780441013593"},
    )

    assert response.status_code == 409
    assert client.get(f"/books/{second['id']}").get_json()["isbn"] == "9780441569595"


def test_update_book_may_keep_its_own_isbn(client, sample_book):
    book_id = client.post("/books", json=sample_book).get_json()["id"]

    response = client.put(
        f"/books/{book_id}",
        json={"title": "Same Book", "author": "Andrew Hunt",
              "isbn": sample_book["isbn"]},
    )

    assert response.status_code == 200
    assert response.get_json()["title"] == "Same Book"


# -------------------------------------------------------------------- delete


def test_delete_book_returns_204_and_removes_it(client, sample_book):
    book_id = client.post("/books", json=sample_book).get_json()["id"]

    response = client.delete(f"/books/{book_id}")

    assert response.status_code == 204
    assert response.get_data() == b""
    assert client.get(f"/books/{book_id}").status_code == 404
    assert client.get("/books").get_json() == []


def test_delete_missing_book_returns_404(client):
    response = client.delete("/books/999")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Book 999 not found"


# ---------------------------------------------------------------- misc/errors


def test_unknown_route_returns_json_404(client):
    response = client.get("/nope")

    assert response.status_code == 404
    assert response.is_json
    assert "error" in response.get_json()


def test_wrong_method_returns_json_405(client):
    response = client.patch("/books")

    assert response.status_code == 405
    assert response.is_json
    assert "error" in response.get_json()


def test_unknown_fields_are_rejected(client):
    response = client.post(
        "/books", json={"title": "Dune", "author": "Herbert", "publisher": "Ace"}
    )

    assert response.status_code == 400
    assert "publisher" in response.get_json()["details"]["body"]


def test_full_crud_lifecycle(client):
    created = client.post(
        "/books", json={"title": "Dune", "author": "Frank Herbert", "year": 1965}
    ).get_json()

    assert client.get("/books").get_json() == [created]

    updated = client.put(
        f"/books/{created['id']}",
        json={"title": "Dune", "author": "Frank Herbert", "year": 1966},
    ).get_json()
    assert updated["year"] == 1966
    assert updated["created_at"] == created["created_at"]

    assert client.delete(f"/books/{created['id']}").status_code == 204
    assert client.get("/books").get_json() == []
    assert client.get("/health").status_code == 200
