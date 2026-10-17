"""Endpoint tests run through Flask's test client against a real SQLite file."""

import json
import sqlite3
from datetime import date

import pytest

import database
from app import create_app

VALID_BOOK = {
    "title": "Nineteen Eighty-Four",
    "author": "George Orwell",
    "year": 1949,
    "isbn": "978-0-451-52493-5",
}


@pytest.fixture
def client(tmp_path):
    return create_app(str(tmp_path / "books.db")).test_client()


@pytest.fixture
def add_book(client):
    """POST a book (VALID_BOOK unless overridden) and return its JSON representation."""

    def _add(**overrides):
        response = client.post("/books", json={**VALID_BOOK, **overrides})
        assert response.status_code == 201, response.get_json()
        return response.get_json()

    return _add


# Health


def test_health_reports_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_health_returns_503_when_database_is_unreadable(client, monkeypatch):
    def unreadable(conn):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(database, "ping", unreadable)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.get_json() == {"status": "error"}


# Create


def test_create_book_returns_201_and_location_header(client):
    response = client.post("/books", json=VALID_BOOK)

    assert response.status_code == 201
    assert response.get_json() == {"id": 1, **VALID_BOOK}
    assert response.headers["Location"] == "/books/1"


def test_create_book_treats_null_year_and_isbn_as_absent(client):
    payload = {
        "title": "Untitled Notes",
        "author": "Anonymous",
        "year": None,
        "isbn": None,
    }

    response = client.post("/books", json=payload)

    assert response.status_code == 201
    assert response.get_json()["year"] is None
    assert response.get_json()["isbn"] is None


def test_create_book_accepts_json_sent_without_content_type(client):
    response = client.post("/books", data=json.dumps(VALID_BOOK))

    assert response.status_code == 201


@pytest.mark.parametrize(
    "payload, field",
    [
        ({"author": "George Orwell"}, "title"),
        ({"title": "1984"}, "author"),
        ({"title": None, "author": "George Orwell"}, "title"),
        ({"title": "", "author": "George Orwell"}, "title"),
        ({"title": "   ", "author": "George Orwell"}, "title"),
        ({"title": "1984", "author": ""}, "author"),
        ({"title": 1984, "author": "George Orwell"}, "title"),
        ({"title": "1984", "author": ["George Orwell"]}, "author"),
    ],
)
def test_create_rejects_missing_or_blank_title_and_author(client, payload, field):
    response = client.post("/books", json=payload)

    assert response.status_code == 400
    assert response.get_json()["error"] == "Validation failed."
    assert field in response.get_json()["details"]
    assert client.get("/books").get_json() == []


@pytest.mark.parametrize(
    "overrides, field",
    [
        ({"year": "1949"}, "year"),
        ({"year": 1949.5}, "year"),
        ({"year": True}, "year"),
        ({"year": 0}, "year"),
        ({"year": date.today().year + 2}, "year"),
        ({"isbn": "12345"}, "isbn"),
        ({"isbn": "978045152493X"}, "isbn"),
        ({"isbn": 9780451524935}, "isbn"),
    ],
)
def test_create_rejects_invalid_year_or_isbn(client, overrides, field):
    response = client.post("/books", json={**VALID_BOOK, **overrides})

    assert response.status_code == 400
    assert field in response.get_json()["details"]


@pytest.mark.parametrize(
    "isbn",
    ["0-306-40615-2", "0-8044-2957-X", "9780451524935", "978-0-451-52493-5"],
)
def test_create_accepts_isbn10_and_isbn13_formats(client, isbn):
    response = client.post("/books", json={**VALID_BOOK, "isbn": isbn})

    assert response.status_code == 201
    assert response.get_json()["isbn"] == isbn


def test_create_accepts_next_calendar_year_as_publication_year(client):
    response = client.post("/books", json={**VALID_BOOK, "year": date.today().year + 1})

    assert response.status_code == 201


# List and filter


def test_list_returns_all_books_in_id_order(client, add_book):
    first = add_book(title="Dune", author="Frank Herbert")
    second = add_book(title="Emma", author="Jane Austen")

    response = client.get("/books")

    assert response.status_code == 200
    assert response.get_json() == [first, second]


def test_list_returns_empty_array_when_there_are_no_books(client):
    response = client.get("/books")

    assert response.status_code == 200
    assert response.get_json() == []


def test_list_filters_by_author_ignoring_case(client, add_book):
    orwell = add_book(title="1984", author="George Orwell")
    add_book(title="Dune", author="Frank Herbert")
    animal_farm = add_book(title="Animal Farm", author="GEORGE ORWELL")

    response = client.get("/books", query_string={"author": "george orwell"})

    assert response.status_code == 200
    assert response.get_json() == [orwell, animal_farm]


def test_list_author_filter_is_case_insensitive_for_non_ascii_names(client, add_book):
    marquez = add_book(
        title="Love in the Time of Cholera", author="Gabriel García Márquez"
    )

    response = client.get("/books", query_string={"author": "GARCÍA"})

    assert response.get_json() == [marquez]


def test_list_author_filter_matches_part_of_the_name(client, add_book):
    orwell = add_book(title="1984", author="George Orwell")
    add_book(title="Dune", author="Frank Herbert")

    response = client.get("/books?author=orwell")

    assert response.get_json() == [orwell]


def test_list_author_filter_with_no_matches_returns_empty_array(client, add_book):
    add_book()

    response = client.get("/books?author=Tolkien")

    assert response.status_code == 200
    assert response.get_json() == []


def test_list_rejects_blank_author_filter(client):
    response = client.get("/books?author=%20%20")

    assert response.status_code == 400
    assert response.get_json()["details"] == {"author": "must not be blank"}


# Get one


def test_get_book_returns_the_stored_book(client, add_book):
    book = add_book()

    response = client.get(f"/books/{book['id']}")

    assert response.status_code == 200
    assert response.get_json() == book


@pytest.mark.parametrize(
    "path", ["/books/999", "/books/abc", "/books/99999999999999999999999"]
)
def test_get_unknown_book_returns_json_404(client, path):
    response = client.get(path)

    assert response.status_code == 404
    assert response.is_json
    assert "error" in response.get_json()


# Update


def test_update_replaces_every_field(client, add_book):
    book = add_book()
    replacement = {
        "title": "Animal Farm",
        "author": "George Orwell",
        "year": 1945,
        "isbn": "978-0-45-152634-6",
    }

    response = client.put(f"/books/{book['id']}", json=replacement)

    assert response.status_code == 200
    assert response.get_json() == {"id": book["id"], **replacement}
    assert client.get(f"/books/{book['id']}").get_json() == {
        "id": book["id"],
        **replacement,
    }


def test_update_clears_optional_fields_that_are_omitted(client, add_book):
    book = add_book()

    response = client.put(
        f"/books/{book['id']}", json={"title": "1984", "author": "George Orwell"}
    )

    assert response.status_code == 200
    assert response.get_json()["year"] is None
    assert response.get_json()["isbn"] is None


def test_update_requires_title_and_author_and_leaves_book_unchanged(client, add_book):
    book = add_book()

    response = client.put(f"/books/{book['id']}", json={"title": "Changed"})

    assert response.status_code == 400
    assert "author" in response.get_json()["details"]
    assert client.get(f"/books/{book['id']}").get_json() == book


def test_update_unknown_book_returns_404(client):
    response = client.put("/books/42", json=VALID_BOOK)

    assert response.status_code == 404
    assert response.is_json


# Delete


def test_delete_removes_the_book(client, add_book):
    book = add_book()

    response = client.delete(f"/books/{book['id']}")

    assert response.status_code == 204
    assert response.data == b""
    assert client.get(f"/books/{book['id']}").status_code == 404


def test_delete_unknown_book_returns_404(client):
    response = client.delete("/books/42")

    assert response.status_code == 404
    assert response.is_json


# Request handling and errors


def test_create_rejects_bodies_that_are_not_a_json_object(client):
    for body in ["{not json", '["a", "list"]', "null", ""]:
        response = client.post("/books", data=body, content_type="application/json")

        assert response.status_code == 400, body
        assert response.is_json
        assert "error" in response.get_json()


def test_unknown_route_returns_json_404(client):
    response = client.get("/nope")

    assert response.status_code == 404
    assert response.is_json


def test_wrong_method_returns_405_with_allow_header(client):
    response = client.post("/books/1")

    assert response.status_code == 405
    assert {"GET", "PUT", "DELETE"} <= set(response.headers["Allow"].split(", "))


def test_unexpected_errors_return_json_500(client, monkeypatch):
    def explode(conn, book):
        raise RuntimeError("boom")

    monkeypatch.setattr(database, "insert_book", explode)

    response = client.post("/books", json=VALID_BOOK)

    assert response.status_code == 500
    assert response.get_json() == {"error": "Internal server error."}


def test_books_persist_across_app_instances(tmp_path):
    db_path = str(tmp_path / "books.db")
    created = (
        create_app(db_path).test_client().post("/books", json=VALID_BOOK).get_json()
    )

    restarted = create_app(db_path).test_client()

    assert restarted.get(f"/books/{created['id']}").get_json() == created
