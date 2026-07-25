"""Integration tests driving the HTTP API end to end against real SQLite."""

from __future__ import annotations

import sqlite3

import pytest

import repository
from app import create_app
from conftest import SAMPLE_BOOK

OTHER_BOOK = {"title": "A Wizard of Earthsea", "author": "Ursula K. Le Guin"}
THIRD_BOOK = {"title": "Neuromancer", "author": "William Gibson", "year": 1984}


class TestHealth:
    def test_reports_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.get_json() == {"status": "ok", "database": "ok"}

    def test_reports_503_when_the_database_is_broken(self, app, database_path):
        with open(database_path, "wb") as handle:
            handle.write(b"this is not a sqlite database")
        response = app.test_client().get("/health")
        assert response.status_code == 503
        assert response.get_json()["error"] == "Database unavailable"


class TestCreate:
    def test_returns_201_with_the_created_resource(self, client):
        response = client.post("/books", json=SAMPLE_BOOK)

        assert response.status_code == 201
        assert response.mimetype == "application/json"
        body = response.get_json()
        assert isinstance(body["id"], int)
        assert {key: body[key] for key in SAMPLE_BOOK} == SAMPLE_BOOK
        assert body["created_at"] == body["updated_at"]
        assert response.headers["Location"] == f"/books/{body['id']}"

    def test_created_book_is_immediately_retrievable(self, client):
        created = client.post("/books", json=SAMPLE_BOOK).get_json()
        assert client.get(f"/books/{created['id']}").get_json() == created

    def test_optional_fields_may_be_omitted(self, client):
        body = client.post("/books", json=OTHER_BOOK).get_json()
        assert body["year"] is None
        assert body["isbn"] is None

    def test_ids_are_unique_per_book(self, client):
        first = client.post("/books", json=OTHER_BOOK).get_json()
        second = client.post("/books", json=THIRD_BOOK).get_json()
        assert first["id"] != second["id"]

    @pytest.mark.parametrize(
        ("payload", "invalid_field"),
        [
            ({"author": "Frank Herbert"}, "title"),
            ({"title": "Dune"}, "author"),
            ({"title": "  ", "author": "Frank Herbert"}, "title"),
            ({"title": "Dune", "author": ""}, "author"),
            ({"title": "Dune", "author": "F. H.", "year": "old"}, "year"),
            ({"title": "Dune", "author": "F. H.", "isbn": "12345"}, "isbn"),
            ({"title": "Dune", "author": "F. H.", "pages": 412}, "pages"),
        ],
    )
    def test_rejects_invalid_payloads(self, client, payload, invalid_field):
        response = client.post("/books", json=payload)

        assert response.status_code == 400
        body = response.get_json()
        assert body["error"] == "Validation failed"
        assert invalid_field in body["details"]
        assert client.get("/books").get_json() == []

    def test_rejects_malformed_json(self, client):
        response = client.post(
            "/books", data="{not json", content_type="application/json"
        )
        assert response.status_code == 400
        assert response.get_json()["details"] == {
            "body": "Request body must be valid JSON"
        }

    def test_rejects_a_duplicate_isbn(self, client, created_book):
        response = client.post(
            "/books", json={**SAMPLE_BOOK, "title": "Same ISBN, different book"}
        )
        assert response.status_code == 409
        assert SAMPLE_BOOK["isbn"] in response.get_json()["error"]

    def test_hyphenated_isbn_is_normalised(self, client):
        body = client.post(
            "/books", json={**SAMPLE_BOOK, "isbn": "978-0-441-47812-5"}
        ).get_json()
        assert body["isbn"] == "9780441478125"

    def test_missing_isbn_does_not_count_as_a_duplicate(self, client):
        assert client.post("/books", json=OTHER_BOOK).status_code == 201
        assert client.post("/books", json=THIRD_BOOK).status_code == 201


class TestList:
    def test_returns_an_empty_list_when_there_are_no_books(self, client):
        response = client.get("/books")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_returns_every_book_most_recent_first(self, client):
        first = client.post("/books", json=OTHER_BOOK).get_json()
        second = client.post("/books", json=THIRD_BOOK).get_json()

        assert [book["id"] for book in client.get("/books").get_json()] == [
            second["id"],
            first["id"],
        ]

    def test_filters_by_author(self, client):
        client.post("/books", json=SAMPLE_BOOK)
        client.post("/books", json=OTHER_BOOK)
        client.post("/books", json=THIRD_BOOK)

        books = client.get("/books?author=Ursula K. Le Guin").get_json()

        assert {book["title"] for book in books} == {
            SAMPLE_BOOK["title"],
            OTHER_BOOK["title"],
        }

    @pytest.mark.parametrize(
        "query", ["ursula k. le guin", "URSULA K. LE GUIN", "  Ursula K. Le Guin  "]
    )
    def test_author_filter_ignores_case_and_surrounding_space(self, client, query):
        client.post("/books", json=OTHER_BOOK)
        assert len(client.get("/books", query_string={"author": query}).get_json()) == 1

    def test_unknown_author_yields_an_empty_list(self, client, created_book):
        response = client.get("/books?author=Nobody At All")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_partial_author_names_do_not_match(self, client, created_book):
        assert client.get("/books?author=Ursula").get_json() == []


class TestRead:
    def test_returns_the_requested_book(self, client, created_book):
        response = client.get(f"/books/{created_book['id']}")
        assert response.status_code == 200
        assert response.get_json() == created_book

    def test_unknown_id_returns_404_json(self, client):
        response = client.get("/books/999")
        assert response.status_code == 404
        assert response.mimetype == "application/json"
        assert response.get_json()["error"] == "No book with id 999"

    def test_non_numeric_id_returns_404_json(self, client):
        response = client.get("/books/abc")
        assert response.status_code == 404
        assert response.mimetype == "application/json"


class TestUpdate:
    def test_replaces_the_stored_fields(self, client, created_book):
        payload = {
            "title": "The Dispossessed",
            "author": "Ursula K. Le Guin",
            "year": 1974,
            "isbn": "978-0-06-051275-4",
        }

        response = client.put(f"/books/{created_book['id']}", json=payload)

        assert response.status_code == 200
        body = response.get_json()
        assert body["id"] == created_book["id"]
        assert body["title"] == "The Dispossessed"
        assert body["year"] == 1974
        assert body["isbn"] == "9780060512754"
        assert body["created_at"] == created_book["created_at"]
        assert client.get(f"/books/{created_book['id']}").get_json() == body

    def test_put_is_a_full_replacement_so_omitted_fields_are_cleared(
        self, client, created_book
    ):
        body = client.put(
            f"/books/{created_book['id']}",
            json={"title": "Rocannon's World", "author": "Ursula K. Le Guin"},
        ).get_json()

        assert body["year"] is None
        assert body["isbn"] is None

    def test_unknown_id_returns_404(self, client):
        response = client.put("/books/999", json=OTHER_BOOK)
        assert response.status_code == 404
        assert response.get_json()["error"] == "No book with id 999"

    def test_invalid_payload_returns_400_and_changes_nothing(self, client, created_book):
        response = client.put(f"/books/{created_book['id']}", json={"title": "Only"})

        assert response.status_code == 400
        assert "author" in response.get_json()["details"]
        assert client.get(f"/books/{created_book['id']}").get_json() == created_book

    def test_taking_another_books_isbn_returns_409(self, client, created_book):
        other = client.post("/books", json=OTHER_BOOK).get_json()

        response = client.put(
            f"/books/{other['id']}", json={**OTHER_BOOK, "isbn": SAMPLE_BOOK["isbn"]}
        )

        assert response.status_code == 409

    def test_keeping_its_own_isbn_is_allowed(self, client, created_book):
        response = client.put(
            f"/books/{created_book['id']}", json={**SAMPLE_BOOK, "year": 2003}
        )
        assert response.status_code == 200
        assert response.get_json()["year"] == 2003


class TestDelete:
    def test_removes_the_book(self, client, created_book):
        response = client.delete(f"/books/{created_book['id']}")

        assert response.status_code == 204
        assert response.get_data() == b""
        assert client.get(f"/books/{created_book['id']}").status_code == 404
        assert client.get("/books").get_json() == []

    def test_deleting_twice_returns_404(self, client, created_book):
        client.delete(f"/books/{created_book['id']}")
        assert client.delete(f"/books/{created_book['id']}").status_code == 404

    def test_unknown_id_returns_404(self, client):
        assert client.delete("/books/999").status_code == 404

    def test_frees_the_isbn_for_reuse(self, client, created_book):
        client.delete(f"/books/{created_book['id']}")
        assert client.post("/books", json=SAMPLE_BOOK).status_code == 201


class TestPersistence:
    def test_books_survive_an_application_restart(self, database_path):
        first_app = create_app({"DATABASE": database_path, "TESTING": True})
        created = first_app.test_client().post("/books", json=SAMPLE_BOOK).get_json()

        second_app = create_app({"DATABASE": database_path, "TESTING": True})
        response = second_app.test_client().get(f"/books/{created['id']}")

        assert response.status_code == 200
        assert response.get_json() == created

    def test_rows_land_in_the_books_table(self, client, database_path, created_book):
        with sqlite3.connect(database_path) as connection:
            row = connection.execute(
                "SELECT title, author, year, isbn FROM books WHERE id = ?",
                (created_book["id"],),
            ).fetchone()
        assert row == tuple(SAMPLE_BOOK[key] for key in ("title", "author", "year", "isbn"))


class TestProtocol:
    def test_unknown_route_returns_404_json(self, client):
        response = client.get("/authors")
        assert response.status_code == 404
        assert response.mimetype == "application/json"
        assert "error" in response.get_json()

    def test_unsupported_method_returns_405_json(self, client):
        response = client.patch("/books/1", json={})
        assert response.status_code == 405
        assert response.mimetype == "application/json"

    def test_json_content_type_is_not_required(self, client):
        response = client.post("/books", data='{"title": "Dune", "author": "F. H."}')
        assert response.status_code == 201

    def test_unexpected_errors_become_500_json(self, database_path, monkeypatch):
        production_app = create_app({"DATABASE": database_path})
        monkeypatch.setattr(
            repository, "list_all", lambda *a, **kw: 1 / 0, raising=True
        )

        response = production_app.test_client().get("/books")

        assert response.status_code == 500
        assert response.get_json() == {"error": "Internal server error"}

    def test_unexpected_errors_propagate_while_testing(self, client, monkeypatch):
        monkeypatch.setattr(repository, "list_all", lambda *a, **kw: 1 / 0)
        with pytest.raises(ZeroDivisionError):
            client.get("/books")
