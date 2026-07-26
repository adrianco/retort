"""End-to-end tests driving the API through Flask's test client."""

from __future__ import annotations

import pytest

from .conftest import HUXLEY, ORWELL


def create(client, payload):
    return client.post("/books", json=payload)


def test_health_reports_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}


def test_create_book_returns_201_with_the_stored_resource(client):
    response = create(client, ORWELL)

    assert response.status_code == 201
    book = response.get_json()
    assert book["id"] > 0
    assert book["title"] == "1984"
    assert book["author"] == "George Orwell"
    assert book["year"] == 1949
    assert book["isbn"] == "9780451524935"
    assert book["created_at"] == book["updated_at"]
    assert response.headers["Location"].endswith(f"/books/{book['id']}")


def test_created_book_is_readable_by_id(client):
    created = create(client, ORWELL).get_json()

    response = client.get(f"/books/{created['id']}")

    assert response.status_code == 200
    assert response.get_json() == created


def test_create_trims_whitespace_and_normalises_isbn(client):
    book = create(
        client, {"title": "  Dune  ", "author": " Frank Herbert ", "isbn": "0-441-01359-7"}
    ).get_json()

    assert book["title"] == "Dune"
    assert book["author"] == "Frank Herbert"
    assert book["isbn"] == "0441013597"
    assert book["year"] is None


def test_create_ignores_unknown_and_client_supplied_fields(client):
    book = create(
        client, {**ORWELL, "id": 999, "created_at": "1900-01-01T00:00:00Z", "pages": 328}
    ).get_json()

    assert book["id"] != 999
    assert book["created_at"] != "1900-01-01T00:00:00Z"
    assert "pages" not in book


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"author": "George Orwell"}, "title"),
        ({"title": "1984"}, "author"),
        ({"title": "   ", "author": "George Orwell"}, "title"),
        ({"title": "1984", "author": 42}, "author"),
        ({"title": "1984", "author": "George Orwell", "year": "1949"}, "year"),
        ({"title": "1984", "author": "George Orwell", "year": 3999}, "year"),
        ({"title": "1984", "author": "George Orwell", "isbn": "123"}, "isbn"),
        # Right shape, wrong check digit — a transposed or mistyped ISBN.
        ({"title": "1984", "author": "George Orwell", "isbn": "9780451524936"}, "isbn"),
        ({"title": "1984", "author": "George Orwell", "isbn": "0-06-085052-4"}, "isbn"),
    ],
)
def test_invalid_payloads_are_rejected_with_400(client, payload, field):
    response = create(client, payload)

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "validation_failed"
    assert field in body["details"]


def test_validation_reports_every_bad_field_at_once(client):
    response = create(client, {"year": "soon"})

    assert response.status_code == 400
    assert set(response.get_json()["details"]) == {"title", "author", "year"}


def test_nothing_is_persisted_when_validation_fails(client):
    create(client, {"title": "No Author"})

    assert client.get("/books").get_json() == []


def test_list_returns_all_books_in_creation_order(client):
    create(client, ORWELL)
    create(client, HUXLEY)

    response = client.get("/books")

    assert response.status_code == 200
    books = response.get_json()
    assert [book["title"] for book in books] == ["1984", "Brave New World"]


def test_list_filters_by_author_case_insensitively(client):
    create(client, ORWELL)
    create(client, HUXLEY)

    response = client.get("/books", query_string={"author": "orwell"})

    assert response.status_code == 200
    books = response.get_json()
    assert len(books) == 1
    assert books[0]["author"] == "George Orwell"


def test_author_filter_with_no_match_returns_an_empty_list(client):
    create(client, ORWELL)

    assert client.get("/books", query_string={"author": "Tolkien"}).get_json() == []


def test_author_filter_treats_wildcards_literally(client):
    create(client, ORWELL)

    assert client.get("/books", query_string={"author": "%"}).get_json() == []


def test_put_replaces_every_field_and_bumps_updated_at(client):
    created = create(client, ORWELL).get_json()

    response = client.put(
        f"/books/{created['id']}",
        json={"title": "Nineteen Eighty-Four", "author": "Eric Blair"},
    )

    assert response.status_code == 200
    updated = response.get_json()
    assert updated["id"] == created["id"]
    assert updated["title"] == "Nineteen Eighty-Four"
    assert updated["author"] == "Eric Blair"
    # Omitted optional fields are cleared: PUT replaces the whole resource.
    assert updated["year"] is None
    assert updated["isbn"] is None
    assert updated["created_at"] == created["created_at"]
    assert client.get(f"/books/{created['id']}").get_json() == updated


def test_put_can_keep_a_books_own_isbn(client):
    created = create(client, ORWELL).get_json()

    response = client.put(f"/books/{created['id']}", json={**ORWELL, "year": 1950})

    assert response.status_code == 200
    assert response.get_json()["isbn"] == created["isbn"]


def test_put_validates_its_payload(client):
    created = create(client, ORWELL).get_json()

    response = client.put(f"/books/{created['id']}", json={"title": "Only a title"})

    assert response.status_code == 400
    assert "author" in response.get_json()["details"]


def test_delete_removes_the_book(client):
    created = create(client, ORWELL).get_json()

    response = client.delete(f"/books/{created['id']}")

    assert response.status_code == 204
    assert response.get_data() == b""
    assert client.get(f"/books/{created['id']}").status_code == 404


def test_duplicate_isbn_is_rejected_with_409(client):
    create(client, ORWELL)

    response = create(
        client,
        {"title": "1984 reprint", "author": "G. Orwell", "isbn": ORWELL["isbn"]},
    )

    assert response.status_code == 409
    assert response.get_json()["error"] == "duplicate_isbn"


def test_books_without_an_isbn_do_not_collide(client):
    first = create(client, {"title": "Untitled", "author": "Anon"})
    second = create(client, {"title": "Untitled", "author": "Anon"})

    assert first.status_code == 201
    assert second.status_code == 201
    assert len(client.get("/books").get_json()) == 2


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_unknown_ids_return_a_json_404(client, method):
    response = getattr(client, method)("/books/4242", json=ORWELL)

    assert response.status_code == 404
    assert response.get_json()["error"] == "not_found"


def test_non_numeric_id_returns_a_json_404(client):
    response = client.get("/books/not-a-number")

    assert response.status_code == 404
    assert response.get_json()["error"] == "not_found"


def test_malformed_json_returns_400(client):
    response = client.post(
        "/books", data="{not json", content_type="application/json"
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_json"


def test_non_json_content_type_returns_415(client):
    response = client.post("/books", data="title=1984")

    assert response.status_code == 415
    assert response.get_json()["error"] == "unsupported_media_type"


def test_json_array_body_is_rejected(client):
    response = client.post("/books", json=[ORWELL])

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_request"


def test_unsupported_method_returns_a_json_405(client):
    response = client.delete("/books")

    assert response.status_code == 405
    assert response.get_json()["error"] == "method_not_allowed"


def test_data_survives_a_restart_of_the_application(app, client):
    created = create(client, ORWELL).get_json()

    # A second app object over the same file stands in for a process restart.
    from bookapi import create_app

    reopened = create_app(database=app.config["DATABASE"]).test_client()

    assert reopened.get(f"/books/{created['id']}").get_json() == created


def test_isbn_errors_distinguish_shape_from_check_digit(client):
    wrong_shape = create(client, {**ORWELL, "isbn": "12345"}).get_json()
    wrong_digit = create(client, {**ORWELL, "isbn": "9780451524936"}).get_json()

    assert "10 or 13 digits" in wrong_shape["details"]["isbn"]
    assert "check digit" in wrong_digit["details"]["isbn"]
