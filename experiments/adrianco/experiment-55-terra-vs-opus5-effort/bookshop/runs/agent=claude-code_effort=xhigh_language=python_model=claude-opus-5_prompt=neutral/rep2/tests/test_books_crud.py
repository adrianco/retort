"""Integration tests for the /books endpoints."""

import sqlite3

import pytest

from bookapi import create_app

from .conftest import EMMA, GATSBY


class TestCreate:
    def test_returns_201_with_the_stored_book(self, client):
        response = client.post("/books", json=GATSBY)

        assert response.status_code == 201
        assert response.headers["Content-Type"].startswith("application/json")
        book = response.get_json()
        assert isinstance(book["id"], int)
        assert {k: book[k] for k in GATSBY} == GATSBY

    def test_sets_a_location_header_pointing_at_the_new_book(self, client):
        response = client.post("/books", json=GATSBY)

        location = response.headers["Location"]
        assert location == f"/books/{response.get_json()['id']}"
        assert client.get(location).status_code == 200

    def test_optional_fields_default_to_null(self, client):
        response = client.post("/books", json={"title": "Untitled", "author": "Anon"})

        assert response.status_code == 201
        assert response.get_json()["year"] is None
        assert response.get_json()["isbn"] is None

    def test_ids_are_unique_per_book(self, add_book):
        assert add_book()["id"] != add_book()["id"]

    def test_trims_surrounding_whitespace(self, client):
        response = client.post(
            "/books", json={"title": "  Emma  ", "author": "\tJane Austen\n"}
        )

        assert response.get_json()["title"] == "Emma"
        assert response.get_json()["author"] == "Jane Austen"

    def test_hyphenated_isbn_is_accepted_and_echoed_back(self, client):
        response = client.post("/books", json={**GATSBY, "isbn": "978-0-306-40615-7"})

        assert response.status_code == 201
        assert response.get_json()["isbn"] == "978-0-306-40615-7"


class TestList:
    def test_empty_collection_is_an_empty_list(self, client):
        response = client.get("/books")

        assert response.status_code == 200
        assert response.get_json() == []

    def test_returns_every_book_ordered_by_id(self, client, add_book):
        first = add_book()
        second = add_book(**EMMA, isbn=None)

        response = client.get("/books")

        assert response.status_code == 200
        assert [b["id"] for b in response.get_json()] == [first["id"], second["id"]]

    def test_author_filter_selects_matching_books_only(self, client, add_book):
        add_book()
        emma = add_book(**EMMA, isbn=None)

        response = client.get("/books?author=Jane Austen")

        assert response.status_code == 200
        assert response.get_json() == [emma]

    def test_author_filter_ignores_case(self, client, add_book):
        emma = add_book(**EMMA, isbn=None)

        assert client.get("/books?author=jane austen").get_json() == [emma]

    def test_author_filter_without_matches_returns_empty_list(self, client, add_book):
        add_book()

        assert client.get("/books?author=Nobody").get_json() == []

    def test_blank_author_filter_is_ignored(self, client, add_book):
        add_book()

        assert len(client.get("/books?author=").get_json()) == 1


class TestRetrieve:
    def test_returns_the_requested_book(self, client, add_book):
        created = add_book()

        response = client.get(f"/books/{created['id']}")

        assert response.status_code == 200
        assert response.get_json() == created

    def test_unknown_id_returns_404_json(self, client):
        response = client.get("/books/4242")

        assert response.status_code == 404
        assert response.headers["Content-Type"].startswith("application/json")
        assert "not found" in response.get_json()["error"].lower()

    def test_non_numeric_id_returns_404_json(self, client):
        response = client.get("/books/abc")

        assert response.status_code == 404
        assert "error" in response.get_json()


class TestReplace:
    def test_updates_every_field(self, client, add_book):
        created = add_book()
        replacement = {
            "title": "Tender Is the Night",
            "author": "F. Scott Fitzgerald",
            "year": 1934,
            "isbn": "9780684801544",
        }

        response = client.put(f"/books/{created['id']}", json=replacement)

        assert response.status_code == 200
        assert response.get_json() == {"id": created["id"], **replacement}
        assert client.get(f"/books/{created['id']}").get_json() == response.get_json()

    def test_omitted_optional_fields_are_cleared(self, client, add_book):
        created = add_book()

        response = client.put(
            f"/books/{created['id']}", json={"title": "Emma", "author": "Jane Austen"}
        )

        assert response.status_code == 200
        assert response.get_json()["year"] is None
        assert response.get_json()["isbn"] is None

    def test_unknown_id_returns_404(self, client):
        response = client.put("/books/4242", json=GATSBY)

        assert response.status_code == 404

    def test_missing_required_field_returns_400(self, client, add_book):
        created = add_book()

        response = client.put(f"/books/{created['id']}", json={"title": "No Author"})

        assert response.status_code == 400
        assert "author" in response.get_json()["details"]
        # The stored book is untouched.
        assert client.get(f"/books/{created['id']}").get_json() == created


class TestPatch:
    def test_updates_only_the_supplied_fields(self, client, add_book):
        created = add_book()

        response = client.patch(f"/books/{created['id']}", json={"year": 1926})

        assert response.status_code == 200
        assert response.get_json() == {**created, "year": 1926}

    def test_empty_body_returns_400(self, client, add_book):
        created = add_book()

        response = client.patch(f"/books/{created['id']}", json={})

        assert response.status_code == 400

    def test_unknown_id_returns_404(self, client):
        response = client.patch("/books/4242", json={"year": 1926})

        assert response.status_code == 404


class TestDelete:
    def test_returns_204_and_removes_the_book(self, client, add_book):
        created = add_book()

        response = client.delete(f"/books/{created['id']}")

        assert response.status_code == 204
        assert response.get_data() == b""
        assert client.get(f"/books/{created['id']}").status_code == 404
        assert client.get("/books").get_json() == []

    def test_deleting_twice_returns_404(self, client, add_book):
        created = add_book()
        client.delete(f"/books/{created['id']}")

        assert client.delete(f"/books/{created['id']}").status_code == 404

    def test_unknown_id_returns_404(self, client):
        assert client.delete("/books/4242").status_code == 404

    def test_leaves_other_books_alone(self, client, add_book):
        keep = add_book()
        remove = add_book(**EMMA, isbn=None)

        client.delete(f"/books/{remove['id']}")

        assert client.get("/books").get_json() == [keep]


class TestPersistence:
    def test_books_survive_an_application_restart(self, client, db_path, add_book):
        created = add_book()

        fresh_client = create_app({"DATABASE": str(db_path), "TESTING": True}).test_client()

        assert fresh_client.get(f"/books/{created['id']}").get_json() == created

    def test_rows_are_written_to_the_sqlite_file(self, db_path, add_book):
        created = add_book()

        conn = sqlite3.connect(db_path)
        try:
            row = conn.execute(
                "SELECT title, author, year, isbn FROM books WHERE id = ?",
                (created["id"],),
            ).fetchone()
        finally:
            conn.close()

        assert row == (GATSBY["title"], GATSBY["author"], GATSBY["year"], GATSBY["isbn"])


class TestErrorHandling:
    def test_unsupported_method_returns_405_json(self, client):
        response = client.delete("/books")

        assert response.status_code == 405
        assert response.headers["Content-Type"].startswith("application/json")
        assert response.get_json() == {"error": "Method Not Allowed"}

    def test_unknown_route_returns_404_json(self, client):
        response = client.get("/nope")

        assert response.status_code == 404
        assert response.get_json() == {"error": "Not Found"}

    def test_unexpected_errors_return_500_json(self, db_path):
        app = create_app({"DATABASE": str(db_path)})

        @app.get("/boom")
        def boom():
            raise RuntimeError("kaboom")

        response = app.test_client().get("/boom")

        assert response.status_code == 500
        assert response.get_json() == {"error": "Internal server error"}


def test_health_and_books_are_the_documented_routes(app):
    rules = {
        (rule.rule, method)
        for rule in app.url_map.iter_rules()
        for method in rule.methods
        if method not in {"HEAD", "OPTIONS"}
    }

    assert {
        ("/health", "GET"),
        ("/books", "POST"),
        ("/books", "GET"),
        ("/books/<int:book_id>", "GET"),
        ("/books/<int:book_id>", "PUT"),
        ("/books/<int:book_id>", "DELETE"),
    } <= rules


@pytest.mark.parametrize("method", ["get", "post", "put", "patch", "delete"])
def test_no_endpoint_returns_html(client, method, add_book):
    created = add_book()
    path = "/books" if method in {"get", "post"} else f"/books/{created['id']}"

    response = getattr(client, method)(path, json={"title": "T", "author": "A"})

    assert response.status_code < 500
    if response.status_code != 204:
        assert response.headers["Content-Type"].startswith("application/json")
