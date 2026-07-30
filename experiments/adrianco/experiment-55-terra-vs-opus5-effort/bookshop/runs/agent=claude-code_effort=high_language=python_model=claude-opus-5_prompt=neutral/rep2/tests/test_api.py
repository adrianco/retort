"""Integration tests driving the API through Flask's test client."""

from __future__ import annotations

import pytest

from app import create_app


def post_book(client, **overrides):
    payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965}
    payload.update(overrides)
    return client.post("/books", json=payload)


class TestHealth:
    def test_reports_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.get_json() == {"status": "ok", "database": "ok"}


class TestCreate:
    def test_creates_book_and_returns_201_with_location(self, client, sample_book):
        response = client.post("/books", json=sample_book)

        assert response.status_code == 201
        body = response.get_json()
        assert body["id"] > 0
        assert body["title"] == sample_book["title"]
        assert body["author"] == sample_book["author"]
        assert body["year"] == 1969
        # Hyphens are stripped so the same ISBN is stored one canonical way.
        assert body["isbn"] == "9780441478125"
        assert body["created_at"] == body["updated_at"]
        assert response.headers["Location"].endswith(f"/books/{body['id']}")

        # The Location header points at a fetchable resource.
        assert client.get(response.headers["Location"]).get_json() == body

    def test_optional_fields_default_to_null(self, client):
        body = client.post("/books", json={"title": "Ada", "author": "Ada L."}).get_json()
        assert body["year"] is None
        assert body["isbn"] is None

    def test_trims_surrounding_whitespace(self, client):
        body = post_book(client, title="  Dune  ", author=" Frank Herbert ").get_json()
        assert body["title"] == "Dune"
        assert body["author"] == "Frank Herbert"

    def test_duplicate_isbn_is_rejected_with_409(self, client, sample_book):
        assert client.post("/books", json=sample_book).status_code == 201

        response = client.post("/books", json={**sample_book, "title": "Reprint"})

        assert response.status_code == 409
        assert response.get_json()["details"] == {"isbn": "must be unique"}

    def test_several_books_may_omit_the_isbn(self, client):
        assert post_book(client, title="One").status_code == 201
        assert post_book(client, title="Two").status_code == 201
        assert len(client.get("/books").get_json()) == 2


class TestCreateValidation:
    @pytest.mark.parametrize(
        ("payload", "field"),
        [
            ({"author": "Frank Herbert"}, "title"),
            ({"title": "Dune"}, "author"),
            ({"title": "   ", "author": "Frank Herbert"}, "title"),
            ({"title": "Dune", "author": ""}, "author"),
            ({"title": 42, "author": "Frank Herbert"}, "title"),
            ({"title": "Dune", "author": None}, "author"),
            ({"title": "Dune", "author": "F. H.", "year": "not a year"}, "year"),
            ({"title": "Dune", "author": "F. H.", "year": 99999}, "year"),
            ({"title": "Dune", "author": "F. H.", "year": True}, "year"),
            ({"title": "Dune", "author": "F. H.", "isbn": "12345"}, "isbn"),
            ({"title": "Dune", "author": "F. H.", "isbn": 9780441478125}, "isbn"),
        ],
    )
    def test_invalid_payload_returns_400_naming_the_field(self, client, payload, field):
        response = client.post("/books", json=payload)

        assert response.status_code == 400
        body = response.get_json()
        assert body["error"] == "validation failed"
        assert field in body["details"]

    def test_missing_title_and_author_are_both_reported(self, client):
        details = client.post("/books", json={}).get_json()["details"]
        assert set(details) == {"title", "author"}

    def test_unknown_fields_are_rejected(self, client):
        response = client.post(
            "/books", json={"title": "Dune", "author": "F. H.", "pages": 412}
        )
        assert response.status_code == 400
        assert "pages" in response.get_json()["details"]["_body"]

    def test_non_object_body_is_rejected(self, client):
        assert client.post("/books", json=["Dune"]).status_code == 400

    def test_malformed_json_returns_400(self, client):
        response = client.post(
            "/books", data="{not json", content_type="application/json"
        )
        assert response.status_code == 400
        assert "error" in response.get_json()

    def test_missing_content_type_returns_415(self, client):
        response = client.post("/books", data="title=Dune")
        assert response.status_code == 415
        assert "application/json" in response.get_json()["error"]

    def test_nothing_is_persisted_when_validation_fails(self, client):
        client.post("/books", json={"author": "Frank Herbert"})
        assert client.get("/books").get_json() == []


class TestList:
    @pytest.fixture()
    def library(self, client):
        for title, author in [
            ("Dune", "Frank Herbert"),
            ("Dune Messiah", "Frank Herbert"),
            ("The Dispossessed", "Ursula K. Le Guin"),
        ]:
            assert post_book(client, title=title, author=author).status_code == 201
        return client

    def test_lists_all_books_in_insertion_order(self, library):
        response = library.get("/books")
        assert response.status_code == 200
        assert [book["title"] for book in response.get_json()] == [
            "Dune",
            "Dune Messiah",
            "The Dispossessed",
        ]

    def test_filters_by_author(self, library):
        books = library.get("/books?author=Frank Herbert").get_json()
        assert [book["title"] for book in books] == ["Dune", "Dune Messiah"]

    def test_author_filter_is_case_insensitive(self, library):
        books = library.get("/books?author=frank HERBERT").get_json()
        assert len(books) == 2

    def test_unknown_author_gives_an_empty_list(self, library):
        response = library.get("/books?author=Nobody")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_blank_author_filter_is_ignored(self, library):
        assert len(library.get("/books?author=%20").get_json()) == 3

    def test_empty_collection(self, client):
        assert client.get("/books").get_json() == []


class TestGet:
    def test_returns_the_requested_book(self, client):
        created = post_book(client).get_json()
        response = client.get(f"/books/{created['id']}")
        assert response.status_code == 200
        assert response.get_json() == created

    def test_unknown_id_returns_404_json(self, client):
        response = client.get("/books/999")
        assert response.status_code == 404
        assert response.is_json
        assert "999" in response.get_json()["error"]

    def test_non_numeric_id_returns_404_json(self, client):
        response = client.get("/books/abc")
        assert response.status_code == 404
        assert response.is_json


class TestUpdate:
    def test_put_replaces_every_field(self, client, sample_book):
        created = client.post("/books", json=sample_book).get_json()

        response = client.put(
            f"/books/{created['id']}",
            json={"title": "Updated", "author": "Someone Else"},
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body["id"] == created["id"]
        assert (body["title"], body["author"]) == ("Updated", "Someone Else")
        # Omitted fields are cleared, because PUT replaces the resource.
        assert body["year"] is None
        assert body["isbn"] is None
        assert body["created_at"] == created["created_at"]
        assert client.get(f"/books/{created['id']}").get_json() == body

    def test_put_requires_title_and_author(self, client):
        created = post_book(client).get_json()
        response = client.put(f"/books/{created['id']}", json={"year": 1999})
        assert response.status_code == 400
        assert set(response.get_json()["details"]) == {"title", "author"}

    def test_put_validates_fields(self, client):
        created = post_book(client).get_json()
        response = client.put(
            f"/books/{created['id']}",
            json={"title": "Dune", "author": "F. H.", "isbn": "nope"},
        )
        assert response.status_code == 400

    def test_put_on_unknown_id_returns_404(self, client):
        response = client.put("/books/999", json={"title": "T", "author": "A"})
        assert response.status_code == 404

    def test_put_rejects_an_isbn_owned_by_another_book(self, client, sample_book):
        client.post("/books", json=sample_book)
        other = post_book(client, title="Dune", isbn=None).get_json()

        response = client.put(
            f"/books/{other['id']}",
            json={"title": "Dune", "author": "F. H.", "isbn": sample_book["isbn"]},
        )

        assert response.status_code == 409

    def test_patch_updates_only_the_supplied_fields(self, client, sample_book):
        created = client.post("/books", json=sample_book).get_json()

        response = client.patch(f"/books/{created['id']}", json={"year": 1974})

        assert response.status_code == 200
        body = response.get_json()
        assert body["year"] == 1974
        assert body["title"] == created["title"]
        assert body["isbn"] == created["isbn"]

    def test_patch_with_no_known_field_returns_400(self, client):
        created = post_book(client).get_json()
        response = client.patch(f"/books/{created['id']}", json={})
        assert response.status_code == 400


class TestDelete:
    def test_deletes_the_book(self, client):
        created = post_book(client).get_json()

        response = client.delete(f"/books/{created['id']}")

        assert response.status_code == 204
        assert response.get_data() == b""
        assert client.get(f"/books/{created['id']}").status_code == 404
        assert client.get("/books").get_json() == []

    def test_deleting_twice_returns_404(self, client):
        created = post_book(client).get_json()
        assert client.delete(f"/books/{created['id']}").status_code == 204
        assert client.delete(f"/books/{created['id']}").status_code == 404

    def test_delete_frees_the_isbn(self, client, sample_book):
        created = client.post("/books", json=sample_book).get_json()
        client.delete(f"/books/{created['id']}")
        assert client.post("/books", json=sample_book).status_code == 201


class TestProtocol:
    def test_unsupported_method_returns_405_json(self, client):
        response = client.delete("/books")
        assert response.status_code == 405
        assert response.is_json
        assert response.get_json()["status"] == 405

    def test_unknown_route_returns_404_json(self, client):
        response = client.get("/authors")
        assert response.status_code == 404
        assert response.is_json

    def test_responses_are_json(self, client):
        assert client.get("/books").headers["Content-Type"].startswith(
            "application/json"
        )


class TestPersistence:
    def test_data_survives_a_restart(self, db_path, sample_book):
        first = create_app(database_path=db_path)
        created = first.test_client().post("/books", json=sample_book).get_json()

        # A brand new app object against the same file sees the same rows.
        second = create_app(database_path=db_path)
        response = second.test_client().get(f"/books/{created['id']}")

        assert response.status_code == 200
        assert response.get_json() == created

    def test_ids_are_not_reused_after_a_delete(self, client):
        first = post_book(client, title="One").get_json()
        client.delete(f"/books/{first['id']}")
        second = post_book(client, title="Two").get_json()
        assert second["id"] > first["id"]
