"""Exercises the whole API through ``BookApi.handle`` without a socket."""

import json

import pytest

DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
EMMA = {"title": "Emma", "author": "Jane Austen", "year": 1815}


def send(api, method, target, data=None):
    """Send a request. ``data`` may be a JSON-serialisable value or raw bytes."""
    if data is None:
        body = b""
    elif isinstance(data, bytes):
        body = data
    else:
        body = json.dumps(data).encode("utf-8")
    return api.handle(method, target, body)


def create(api, payload=DUNE):
    response = send(api, "POST", "/books", payload)
    assert response.status == 201
    return response.body


# --- POST /books -----------------------------------------------------------------


def test_post_creates_a_book_and_returns_it_with_location(api):
    response = send(api, "POST", "/books", DUNE)

    assert response.status == 201
    assert response.headers["Location"] == f"/books/{response.body['id']}"
    assert response.body == {"id": response.body["id"], **DUNE}


def test_post_without_year_or_isbn_stores_nulls(api):
    response = send(api, "POST", "/books", {"title": "Emma", "author": "Jane Austen"})

    assert response.status == 201
    assert response.body["year"] is None
    assert response.body["isbn"] is None


def test_post_with_missing_author_returns_400_with_details(api):
    response = send(api, "POST", "/books", {"title": "Dune"})

    assert response.status == 400
    assert response.body == {"error": "Validation failed", "details": {"author": "is required"}}


def test_post_with_malformed_json_returns_400(api):
    response = send(api, "POST", "/books", b'{"title": "Dune",')

    assert response.status == 400
    assert response.body == {"error": "Request body must be valid JSON"}


@pytest.mark.parametrize("raw", [b"", b"\xff\xfe\x00", b"[" * 100_000])
def test_post_with_undecodable_body_returns_400(api, raw):
    response = send(api, "POST", "/books", raw)

    assert response.status == 400
    assert response.body == {"error": "Request body must be valid JSON"}


def test_post_with_non_object_body_returns_400(api):
    response = send(api, "POST", "/books", ["Dune", "Frank Herbert"])

    assert response.status == 400
    assert response.body["details"] == {"body": "must be a JSON object"}


# --- GET /books ------------------------------------------------------------------


def test_list_is_empty_initially(api):
    response = send(api, "GET", "/books")

    assert response.status == 200
    assert response.body == []


def test_list_returns_every_book(api):
    dune = create(api, DUNE)
    emma = create(api, EMMA)

    response = send(api, "GET", "/books")

    assert response.status == 200
    assert response.body == [dune, emma]


def test_list_filters_by_author_query(api):
    dune = create(api, DUNE)
    create(api, EMMA)

    response = send(api, "GET", "/books?author=Frank%20Herbert")

    assert response.status == 200
    assert response.body == [dune]


def test_list_author_filter_is_case_insensitive(api):
    dune = create(api, DUNE)

    response = send(api, "GET", "/books?author=FRANK+HERBERT")

    assert response.body == [dune]


def test_list_author_filter_with_no_matches_returns_empty_list(api):
    create(api, DUNE)

    response = send(api, "GET", "/books?author=Nobody")

    assert response.status == 200
    assert response.body == []


def test_list_rejects_blank_author_filter(api):
    response = send(api, "GET", "/books?author=%20%20")

    assert response.status == 400
    assert response.body == {"error": "The author filter must not be empty"}


# --- GET /books/{id} -------------------------------------------------------------


def test_get_returns_the_book(api):
    book = create(api)

    response = send(api, "GET", f"/books/{book['id']}")

    assert response.status == 200
    assert response.body == book


def test_get_unknown_id_returns_404(api):
    response = send(api, "GET", "/books/999")

    assert response.status == 404
    assert response.body == {"error": "Book not found"}


@pytest.mark.parametrize("book_id", ["abc", "1.5", "-1", "99999999999999999999999"])
def test_non_numeric_or_out_of_range_ids_return_404(api, book_id):
    response = send(api, "GET", f"/books/{book_id}")

    assert response.status == 404


# --- PUT /books/{id} -------------------------------------------------------------


def test_put_replaces_the_book(api):
    book = create(api)
    replacement = {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}

    response = send(api, "PUT", f"/books/{book['id']}", replacement)

    assert response.status == 200
    assert response.body == {"id": book["id"], "isbn": None, **replacement}
    assert send(api, "GET", f"/books/{book['id']}").body == response.body


def test_put_requires_title_and_author(api):
    book = create(api)

    response = send(api, "PUT", f"/books/{book['id']}", {"title": "Dune"})

    assert response.status == 400
    assert response.body["details"] == {"author": "is required"}
    assert send(api, "GET", f"/books/{book['id']}").body == book


def test_put_unknown_id_returns_404(api):
    response = send(api, "PUT", "/books/999", EMMA)

    assert response.status == 404


def test_put_validates_the_payload_before_checking_existence(api):
    response = send(api, "PUT", "/books/999", {"title": ""})

    assert response.status == 400


# --- DELETE /books/{id} ----------------------------------------------------------


def test_delete_removes_the_book(api):
    book = create(api)

    response = send(api, "DELETE", f"/books/{book['id']}")

    assert response.status == 204
    assert response.body is None
    assert send(api, "GET", f"/books/{book['id']}").status == 404


def test_delete_unknown_id_returns_404(api):
    response = send(api, "DELETE", "/books/999")

    assert response.status == 404


# --- routing, health and errors --------------------------------------------------


def test_trailing_slash_is_ignored(api):
    create(api)

    assert send(api, "GET", "/books/").status == 200


def test_unknown_path_returns_404(api):
    response = send(api, "GET", "/authors")

    assert response.status == 404
    assert response.body == {"error": "Not found"}


def test_unsupported_method_returns_405_with_allow_header(api):
    book = create(api)

    response = send(api, "PATCH", f"/books/{book['id']}", {"title": "x"})

    assert response.status == 405
    assert response.headers["Allow"] == "DELETE, GET, PUT"


def test_health_reports_ok(api):
    response = send(api, "GET", "/health")

    assert response.status == 200
    assert response.body == {"status": "ok"}


def test_health_reports_unavailable_when_database_is_closed(api, repository):
    repository.close()

    response = send(api, "GET", "/health")

    assert response.status == 503
    assert response.body == {"status": "unavailable"}


def test_unexpected_failure_returns_500_without_leaking_details(api, monkeypatch):
    def broken(author=None):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(api.repository, "list", broken)

    response = send(api, "GET", "/books")

    assert response.status == 500
    assert response.body == {"error": "Internal server error"}
