"""Integration tests driving the API through Flask's test client."""

from __future__ import annotations

import datetime

import pytest


# --------------------------------------------------------------------------- #
# health
# --------------------------------------------------------------------------- #

def test_health_reports_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}


# --------------------------------------------------------------------------- #
# POST /books
# --------------------------------------------------------------------------- #

def test_create_book_returns_201_with_location_and_body(client):
    response = client.post(
        "/books",
        json={"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"},
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["id"] > 0
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"
    assert body["year"] == 1965
    assert body["isbn"] == "9780441013593"
    assert response.headers["Location"].endswith(f"/books/{body['id']}")


def test_create_book_allows_optional_fields_to_be_omitted(client):
    response = client.post("/books", json={"title": "Untitled", "author": "Anon"})

    assert response.status_code == 201
    body = response.get_json()
    assert body["year"] is None
    assert body["isbn"] is None


def test_create_book_trims_surrounding_whitespace(client):
    body = client.post("/books", json={"title": "  Ubik  ", "author": " P.K. Dick "}).get_json()
    assert (body["title"], body["author"]) == ("Ubik", "P.K. Dick")


def test_created_book_is_persisted_and_retrievable(client, make_book):
    created = make_book()

    fetched = client.get(f"/books/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.get_json() == created


def test_ids_are_unique_per_book(make_book):
    first = make_book(title="One", isbn=None)
    second = make_book(title="Two", isbn=None)
    assert first["id"] != second["id"]


@pytest.mark.parametrize(
    ("payload", "bad_field"),
    [
        ({"author": "No Title"}, "title"),
        ({"title": "No Author"}, "author"),
        ({}, "title"),
        ({"title": "", "author": "A"}, "title"),
        ({"title": "   ", "author": "A"}, "title"),
        ({"title": "T", "author": ""}, "author"),
        ({"title": 42, "author": "A"}, "title"),
        ({"title": None, "author": "A"}, "title"),
        ({"title": "T", "author": ["a", "b"]}, "author"),
        ({"title": "T", "author": "A", "year": "not-a-year"}, "year"),
        ({"title": "T", "author": "A", "year": 3.5}, "year"),
        ({"title": "T", "author": "A", "year": True}, "year"),
        ({"title": "T", "author": "A", "year": 0}, "year"),
        ({"title": "T", "author": "A", "isbn": 12345}, "isbn"),
        ({"title": "T", "author": "A", "isbn": "not an isbn!"}, "isbn"),
    ],
)
def test_create_book_rejects_invalid_payloads(client, payload, bad_field):
    response = client.post("/books", json=payload)

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "Validation failed"
    assert bad_field in body["details"]


def test_create_book_reports_every_invalid_field_at_once(client):
    response = client.post("/books", json={"year": "soon"})

    details = response.get_json()["details"]
    assert set(details) == {"title", "author", "year"}


def test_create_book_rejects_future_year(client):
    far_future = datetime.date.today().year + 5
    response = client.post("/books", json={"title": "T", "author": "A", "year": far_future})
    assert response.status_code == 400
    assert "year" in response.get_json()["details"]


def test_create_book_rejects_non_object_body(client):
    response = client.post("/books", json=["not", "an", "object"])
    assert response.status_code == 400


def test_create_book_rejects_malformed_json(client):
    response = client.post("/books", data="{oops", content_type="application/json")
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_create_book_rejects_empty_body(client):
    assert client.post("/books").status_code == 400


def test_create_book_accepts_json_without_a_content_type_header(client):
    """`curl -d '{...}'` omits Content-Type; the body should still be parsed."""
    response = client.post("/books", data='{"title": "Bare", "author": "A"}')

    assert response.status_code == 201
    assert response.get_json()["title"] == "Bare"


def test_create_book_rejects_a_non_json_body_with_400_not_415(client):
    response = client.post("/books", data="title=Bare&author=A")
    assert response.status_code == 400


def test_duplicate_isbn_is_rejected_with_409(client, make_book):
    make_book(isbn="9780261102217")

    response = client.post(
        "/books", json={"title": "Copy", "author": "Someone", "isbn": "9780261102217"}
    )
    assert response.status_code == 409
    assert "ISBN" in response.get_json()["error"]


def test_books_without_isbn_do_not_collide(client, make_book):
    make_book(title="First", isbn=None)
    make_book(title="Second", isbn=None)
    assert len(client.get("/books").get_json()) == 2


# --------------------------------------------------------------------------- #
# GET /books
# --------------------------------------------------------------------------- #

def test_list_books_is_empty_initially(client):
    response = client.get("/books")
    assert response.status_code == 200
    assert response.get_json() == []


def test_list_books_returns_all_books_ordered_by_id(client, make_book):
    make_book(title="A", isbn=None)
    make_book(title="B", isbn=None)
    make_book(title="C", isbn=None)

    body = client.get("/books").get_json()
    assert [b["title"] for b in body] == ["A", "B", "C"]


def test_list_books_filters_by_author(client, make_book):
    make_book(title="The Hobbit", author="J.R.R. Tolkien", isbn=None)
    make_book(title="Dune", author="Frank Herbert", isbn=None)

    body = client.get("/books?author=Frank Herbert").get_json()
    assert [b["title"] for b in body] == ["Dune"]


def test_author_filter_is_case_insensitive_and_matches_substrings(client, make_book):
    make_book(title="The Hobbit", author="J.R.R. Tolkien", isbn=None)
    make_book(title="Dune", author="Frank Herbert", isbn=None)

    assert len(client.get("/books?author=tolkien").get_json()) == 1
    assert len(client.get("/books?author=TOLKIEN").get_json()) == 1


def test_author_filter_with_no_matches_returns_empty_list(client, make_book):
    make_book()
    response = client.get("/books?author=Nobody")
    assert response.status_code == 200
    assert response.get_json() == []


def test_author_filter_does_not_treat_input_as_a_wildcard(client, make_book):
    make_book(author="Tolkien", isbn=None)
    assert client.get("/books?author=%").get_json() == []


def test_blank_author_filter_is_ignored(client, make_book):
    make_book()
    assert len(client.get("/books?author=").get_json()) == 1


def test_list_books_filters_by_year(client, make_book):
    make_book(title="Old", year=1937, isbn=None)
    make_book(title="New", year=2001, isbn=None)

    body = client.get("/books?year=2001").get_json()
    assert [b["title"] for b in body] == ["New"]


def test_list_books_rejects_non_numeric_year_filter(client):
    response = client.get("/books?year=recent")
    assert response.status_code == 400


def test_filters_combine(client, make_book):
    make_book(title="Match", author="Tolkien", year=1937, isbn=None)
    make_book(title="Wrong year", author="Tolkien", year=1954, isbn=None)
    make_book(title="Wrong author", author="Herbert", year=1937, isbn=None)

    body = client.get("/books?author=tolkien&year=1937").get_json()
    assert [b["title"] for b in body] == ["Match"]


# --------------------------------------------------------------------------- #
# GET /books/{id}
# --------------------------------------------------------------------------- #

def test_get_missing_book_returns_404(client):
    response = client.get("/books/999")
    assert response.status_code == 404
    assert "error" in response.get_json()


def test_get_book_with_non_integer_id_returns_404_json(client):
    response = client.get("/books/abc")
    assert response.status_code == 404
    assert response.is_json


# --------------------------------------------------------------------------- #
# PUT /books/{id}
# --------------------------------------------------------------------------- #

def test_put_updates_all_fields(client, make_book):
    created = make_book()

    response = client.put(
        f"/books/{created['id']}",
        json={
            "title": "The Fellowship of the Ring",
            "author": "J.R.R. Tolkien",
            "year": 1954,
            "isbn": "9780261102354",
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["id"] == created["id"]
    assert body["title"] == "The Fellowship of the Ring"
    assert body["year"] == 1954
    assert body["isbn"] == "9780261102354"


def test_put_persists_the_change(client, make_book):
    created = make_book()
    client.put(f"/books/{created['id']}", json={"title": "Renamed", "author": "Author"})

    assert client.get(f"/books/{created['id']}").get_json()["title"] == "Renamed"


def test_put_clears_omitted_optional_fields(client, make_book):
    created = make_book(year=1937, isbn="9780261102217")

    body = client.put(
        f"/books/{created['id']}", json={"title": "Still Here", "author": "Tolkien"}
    ).get_json()

    assert body["year"] is None
    assert body["isbn"] is None


def test_put_requires_title_and_author(client, make_book):
    created = make_book()

    response = client.put(f"/books/{created['id']}", json={"year": 1954})

    assert response.status_code == 400
    assert set(response.get_json()["details"]) == {"title", "author"}


def test_put_missing_book_returns_404(client):
    response = client.put("/books/999", json={"title": "T", "author": "A"})
    assert response.status_code == 404


def test_put_validates_before_checking_existence(client):
    """An invalid payload is a 400 regardless of whether the book exists."""
    assert client.put("/books/999", json={"title": ""}).status_code == 400


def test_put_rejecting_duplicate_isbn_returns_409(client, make_book):
    make_book(title="First", isbn="9780261102217")
    second = make_book(title="Second", isbn="9780441013593")

    response = client.put(
        f"/books/{second['id']}",
        json={"title": "Second", "author": "Someone", "isbn": "9780261102217"},
    )
    assert response.status_code == 409


def test_put_can_keep_its_own_isbn(client, make_book):
    created = make_book(isbn="9780261102217")

    response = client.put(
        f"/books/{created['id']}",
        json={"title": "New Title", "author": "Tolkien", "isbn": "9780261102217"},
    )
    assert response.status_code == 200


# --------------------------------------------------------------------------- #
# PATCH /books/{id}
# --------------------------------------------------------------------------- #

def test_patch_updates_only_supplied_fields(client, make_book):
    created = make_book(year=1937, isbn="9780261102217")

    response = client.patch(f"/books/{created['id']}", json={"title": "Patched"})

    assert response.status_code == 200
    body = response.get_json()
    assert body["title"] == "Patched"
    assert body["author"] == created["author"]
    assert body["year"] == 1937
    assert body["isbn"] == "9780261102217"


def test_patch_can_clear_an_optional_field(client, make_book):
    created = make_book(year=1937)
    body = client.patch(f"/books/{created['id']}", json={"year": None}).get_json()
    assert body["year"] is None


def test_patch_rejects_empty_payload(client, make_book):
    created = make_book()
    assert client.patch(f"/books/{created['id']}", json={}).status_code == 400


def test_patch_still_validates_supplied_fields(client, make_book):
    created = make_book()
    response = client.patch(f"/books/{created['id']}", json={"title": ""})
    assert response.status_code == 400
    assert "title" in response.get_json()["details"]


# --------------------------------------------------------------------------- #
# DELETE /books/{id}
# --------------------------------------------------------------------------- #

def test_delete_returns_204_and_removes_the_book(client, make_book):
    created = make_book()

    response = client.delete(f"/books/{created['id']}")
    assert response.status_code == 204
    assert response.get_data() == b""

    assert client.get(f"/books/{created['id']}").status_code == 404
    assert client.get("/books").get_json() == []


def test_delete_is_not_idempotent_in_status_code(client, make_book):
    created = make_book()
    assert client.delete(f"/books/{created['id']}").status_code == 204
    assert client.delete(f"/books/{created['id']}").status_code == 404


def test_delete_missing_book_returns_404(client):
    assert client.delete("/books/999").status_code == 404


def test_delete_frees_the_isbn_for_reuse(client, make_book):
    created = make_book(isbn="9780261102217")
    client.delete(f"/books/{created['id']}")

    response = client.post(
        "/books", json={"title": "Reissue", "author": "Tolkien", "isbn": "9780261102217"}
    )
    assert response.status_code == 201


# --------------------------------------------------------------------------- #
# protocol level
# --------------------------------------------------------------------------- #

def test_unknown_route_returns_json_404(client):
    response = client.get("/nope")
    assert response.status_code == 404
    assert response.is_json


def test_unsupported_method_returns_json_405(client):
    response = client.delete("/books")
    assert response.status_code == 405
    assert response.is_json


def test_unknown_fields_in_payload_are_ignored(client):
    response = client.post(
        "/books", json={"title": "T", "author": "A", "publisher": "Unexpected"}
    )
    assert response.status_code == 201
    assert "publisher" not in response.get_json()
