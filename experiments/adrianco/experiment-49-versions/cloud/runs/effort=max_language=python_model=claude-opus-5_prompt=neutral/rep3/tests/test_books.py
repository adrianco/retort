"""End-to-end tests for the book CRUD endpoints."""

from __future__ import annotations

import pytest


class TestCreate:
    def test_returns_201_with_the_created_book(self, client):
        response = client.post(
            "/books",
            json={
                "title": "Nineteen Eighty-Four",
                "author": "George Orwell",
                "year": 1949,
                "isbn": "9780451524935",
            },
        )

        assert response.status_code == 201
        assert response.get_json() == {
            "id": 1,
            "title": "Nineteen Eighty-Four",
            "author": "George Orwell",
            "year": 1949,
            "isbn": "9780451524935",
        }

    def test_sets_a_location_header_pointing_at_the_new_book(self, client):
        response = client.post(
            "/books", json={"title": "Animal Farm", "author": "George Orwell"}
        )
        location = response.headers["Location"]

        assert location.endswith("/books/1")
        assert client.get(location).status_code == 200

    def test_optional_fields_default_to_null(self, client):
        response = client.post(
            "/books", json={"title": "Animal Farm", "author": "George Orwell"}
        )

        body = response.get_json()
        assert body["year"] is None
        assert body["isbn"] is None

    def test_duplicate_isbn_is_rejected_with_409(self, client, add_book):
        existing = add_book()

        response = client.post(
            "/books",
            json={"title": "Reprint", "author": "Someone", "isbn": existing["isbn"]},
        )

        assert response.status_code == 409
        assert response.get_json()["error"] == "conflict"

    def test_books_without_an_isbn_do_not_collide(self, client, add_book):
        add_book(isbn=None)
        add_book(isbn=None)

        assert len(client.get("/books").get_json()) == 2


class TestList:
    def test_returns_an_empty_list_when_there_are_no_books(self, client):
        response = client.get("/books")

        assert response.status_code == 200
        assert response.get_json() == []

    def test_returns_every_book_in_insertion_order(self, client, add_book):
        first = add_book(title="First")
        second = add_book(title="Second")

        body = client.get("/books").get_json()

        assert [book["id"] for book in body] == [first["id"], second["id"]]
        assert [book["title"] for book in body] == ["First", "Second"]

    def test_author_filter_selects_only_matching_books(self, client, add_book):
        add_book(title="Animal Farm", author="George Orwell")
        add_book(title="Brave New World", author="Aldous Huxley")

        body = client.get("/books?author=George Orwell").get_json()

        assert [book["title"] for book in body] == ["Animal Farm"]

    def test_author_filter_is_case_insensitive(self, client, add_book):
        add_book(author="George Orwell")

        assert len(client.get("/books?author=george orwell").get_json()) == 1

    def test_author_filter_with_no_matches_returns_an_empty_list(
        self, client, add_book
    ):
        add_book(author="George Orwell")

        response = client.get("/books?author=Nobody")

        assert response.status_code == 200
        assert response.get_json() == []

    def test_blank_author_filter_is_ignored(self, client, add_book):
        add_book()

        assert len(client.get("/books?author=").get_json()) == 1
        assert len(client.get("/books?author=%20").get_json()) == 1

    def test_author_filter_is_not_vulnerable_to_sql_injection(self, client, add_book):
        add_book(author="George Orwell")

        response = client.get("/books?author=' OR 1=1 --")

        assert response.status_code == 200
        assert response.get_json() == []


class TestRetrieve:
    def test_returns_the_requested_book(self, client, add_book):
        created = add_book()

        response = client.get(f"/books/{created['id']}")

        assert response.status_code == 200
        assert response.get_json() == created

    def test_unknown_id_returns_404(self, client):
        response = client.get("/books/999")

        assert response.status_code == 404
        assert response.get_json()["error"] == "not_found"

    def test_non_numeric_id_returns_404(self, client):
        assert client.get("/books/abc").status_code == 404


class TestReplace:
    def test_updates_every_supplied_field(self, client, add_book):
        created = add_book()

        response = client.put(
            f"/books/{created['id']}",
            json={
                "title": "Animal Farm",
                "author": "Eric Blair",
                "year": 1945,
                "isbn": "9780452284241",
            },
        )

        assert response.status_code == 200
        assert response.get_json() == {
            "id": created["id"],
            "title": "Animal Farm",
            "author": "Eric Blair",
            "year": 1945,
            "isbn": "9780452284241",
        }

    def test_the_change_is_persisted(self, client, add_book):
        created = add_book()

        client.put(
            f"/books/{created['id']}", json={"title": "Renamed", "author": "Author"}
        )

        assert client.get(f"/books/{created['id']}").get_json()["title"] == "Renamed"

    def test_omitted_optional_fields_are_cleared(self, client, add_book):
        created = add_book(year=1949, isbn="9781111111111")

        body = client.put(
            f"/books/{created['id']}",
            json={"title": "Animal Farm", "author": "George Orwell"},
        ).get_json()

        assert body["year"] is None
        assert body["isbn"] is None

    def test_a_book_can_be_round_tripped_from_get_to_put(self, client, add_book):
        """The `id` in a GET response is ignored rather than rejected."""
        created = add_book()
        created["title"] = "Edited"

        response = client.put(f"/books/{created['id']}", json=created)

        assert response.status_code == 200
        assert response.get_json() == created

    def test_unknown_id_returns_404(self, client):
        response = client.put("/books/999", json={"title": "T", "author": "A"})

        assert response.status_code == 404

    def test_taking_another_books_isbn_returns_409(self, client, add_book):
        first = add_book()
        second = add_book()

        response = client.put(
            f"/books/{second['id']}",
            json={"title": "T", "author": "A", "isbn": first["isbn"]},
        )

        assert response.status_code == 409

    def test_keeping_its_own_isbn_is_allowed(self, client, add_book):
        created = add_book()

        response = client.put(
            f"/books/{created['id']}",
            json={"title": "T", "author": "A", "isbn": created["isbn"]},
        )

        assert response.status_code == 200


class TestUpdatePartially:
    def test_only_the_supplied_fields_change(self, client, add_book):
        created = add_book(title="Original", author="George Orwell", year=1949)

        response = client.patch(f"/books/{created['id']}", json={"year": 1950})

        assert response.status_code == 200
        assert response.get_json() == {**created, "year": 1950}

    def test_an_empty_body_is_rejected(self, client, add_book):
        created = add_book()

        response = client.patch(f"/books/{created['id']}", json={})

        assert response.status_code == 400
        assert response.get_json()["error"] == "validation_error"

    def test_unknown_id_returns_404(self, client):
        assert client.patch("/books/999", json={"year": 1950}).status_code == 404


class TestDelete:
    def test_returns_204_with_an_empty_body(self, client, add_book):
        created = add_book()

        response = client.delete(f"/books/{created['id']}")

        assert response.status_code == 204
        assert response.get_data() == b""

    def test_the_book_is_gone_afterwards(self, client, add_book):
        created = add_book()

        client.delete(f"/books/{created['id']}")

        assert client.get(f"/books/{created['id']}").status_code == 404
        assert client.get("/books").get_json() == []

    def test_deleting_twice_returns_404(self, client, add_book):
        created = add_book()
        client.delete(f"/books/{created['id']}")

        assert client.delete(f"/books/{created['id']}").status_code == 404

    def test_other_books_are_untouched(self, client, add_book):
        keep = add_book()
        remove = add_book()

        client.delete(f"/books/{remove['id']}")

        assert [book["id"] for book in client.get("/books").get_json()] == [keep["id"]]


class TestLifecycle:
    def test_full_create_read_update_delete_round_trip(self, client):
        created = client.post(
            "/books",
            json={
                "title": "The Pragmatic Programmer",
                "author": "Andrew Hunt",
                "year": 1999,
                "isbn": "9780201616224",
            },
        ).get_json()
        book_id = created["id"]

        assert client.get(f"/books/{book_id}").get_json() == created
        assert client.get("/books").get_json() == [created]

        updated = client.put(
            f"/books/{book_id}",
            json={
                "title": "The Pragmatic Programmer, 2nd Edition",
                "author": "Andrew Hunt",
                "year": 2019,
                "isbn": "9780135957059",
            },
        ).get_json()

        assert updated["year"] == 2019
        assert client.get(f"/books/{book_id}").get_json() == updated

        assert client.delete(f"/books/{book_id}").status_code == 204
        assert client.get(f"/books/{book_id}").status_code == 404
        assert client.get("/books").get_json() == []

    @pytest.mark.parametrize(
        "method, path",
        [
            ("get", "/books"),
            ("post", "/books"),
            ("get", "/books/1"),
            ("put", "/books/1"),
            ("patch", "/books/1"),
            ("delete", "/books/1"),
            ("get", "/health"),
        ],
    )
    def test_every_endpoint_responds_with_json(self, client, add_book, method, path):
        add_book()
        payload = {"title": "T", "author": "A"}

        response = getattr(client, method)(path, json=payload)

        if response.status_code == 204:
            assert response.get_data() == b""
        else:
            assert response.mimetype == "application/json"
