"""Tests for input validation on POST, PUT and PATCH."""

from __future__ import annotations

import pytest

from bookapi.validation import MAX_TEXT_LENGTH


def post(client, payload):
    return client.post("/books", json=payload)


class TestRequiredFields:
    @pytest.mark.parametrize(
        "payload, missing",
        [
            ({}, ["title", "author"]),
            ({"author": "George Orwell"}, ["title"]),
            ({"title": "Animal Farm"}, ["author"]),
        ],
    )
    def test_title_and_author_are_required(self, client, payload, missing):
        response = post(client, payload)

        assert response.status_code == 400
        body = response.get_json()
        assert body["error"] == "validation_error"
        assert sorted(body["details"]) == sorted(missing)

    @pytest.mark.parametrize("field", ["title", "author"])
    def test_explicit_null_is_rejected(self, client, field):
        payload = {"title": "Animal Farm", "author": "George Orwell", field: None}

        response = post(client, payload)

        assert response.status_code == 400
        assert "must not be null" in response.get_json()["details"][field]

    @pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
    @pytest.mark.parametrize("field", ["title", "author"])
    def test_blank_values_are_rejected(self, client, field, blank):
        payload = {"title": "Animal Farm", "author": "George Orwell", field: blank}

        response = post(client, payload)

        assert response.status_code == 400
        assert "must not be empty" in response.get_json()["details"][field]

    @pytest.mark.parametrize("value", [42, True, ["a"], {"a": 1}])
    @pytest.mark.parametrize("field", ["title", "author"])
    def test_non_string_values_are_rejected(self, client, field, value):
        payload = {"title": "Animal Farm", "author": "George Orwell", field: value}

        response = post(client, payload)

        assert response.status_code == 400
        assert "must be a string" in response.get_json()["details"][field]

    def test_overlong_values_are_rejected(self, client):
        response = post(client, {"title": "x" * (MAX_TEXT_LENGTH + 1), "author": "A"})

        assert response.status_code == 400
        assert "at most" in response.get_json()["details"]["title"]

    def test_surrounding_whitespace_is_trimmed(self, client):
        body = post(
            client, {"title": "  Animal Farm  ", "author": "\tGeorge Orwell\n"}
        ).get_json()

        assert body["title"] == "Animal Farm"
        assert body["author"] == "George Orwell"

    def test_all_invalid_fields_are_reported_at_once(self, client):
        response = post(client, {"title": "", "author": 7, "year": "soon"})

        details = response.get_json()["details"]
        assert sorted(details) == ["author", "title", "year"]


class TestYear:
    @pytest.mark.parametrize(
        "value, expected",
        [(1949, 1949), (None, None), ("1949", 1949), (1949.0, 1949), (-500, -500)],
    )
    def test_accepted_values(self, client, value, expected):
        body = post(client, {"title": "T", "author": "A", "year": value}).get_json()

        assert body["year"] == expected

    @pytest.mark.parametrize(
        "value", ["not a year", 1949.5, True, [1949], {"y": 1949}, "", 99999, -99999]
    )
    def test_rejected_values(self, client, value):
        response = post(client, {"title": "T", "author": "A", "year": value})

        assert response.status_code == 400
        assert "year" in response.get_json()["details"]


class TestIsbn:
    def test_must_be_a_string(self, client):
        response = post(client, {"title": "T", "author": "A", "isbn": 9780451524935})

        assert response.status_code == 400
        assert "must be a string" in response.get_json()["details"]["isbn"]

    def test_blank_is_stored_as_null(self, client):
        body = post(client, {"title": "T", "author": "A", "isbn": "   "}).get_json()

        assert body["isbn"] is None

    def test_hyphenated_isbns_are_kept_as_given(self, client):
        body = post(
            client, {"title": "T", "author": "A", "isbn": "978-0-452-28423-4"}
        ).get_json()

        assert body["isbn"] == "978-0-452-28423-4"

    def test_overlong_isbn_is_rejected(self, client):
        response = post(client, {"title": "T", "author": "A", "isbn": "9" * 33})

        assert response.status_code == 400


class TestRequestBody:
    @pytest.mark.parametrize("body", ["not json", "", "{oops"])
    def test_malformed_json_is_rejected(self, client, body):
        response = client.post(
            "/books", data=body, content_type="application/json"
        )

        assert response.status_code == 400
        assert response.get_json()["error"] == "validation_error"

    @pytest.mark.parametrize("payload", [[], ["a"], "a string", 7])
    def test_a_non_object_body_is_rejected(self, client, payload):
        response = post(client, payload)

        assert response.status_code == 400
        assert "JSON object" in response.get_json()["message"]

    def test_a_wrong_content_type_header_is_tolerated(self, client):
        """`curl -d '{...}'` without an explicit JSON header should still work."""
        response = client.post(
            "/books", data='{"title": "T", "author": "A"}', content_type="text/plain"
        )

        assert response.status_code == 201

    def test_unknown_fields_are_ignored(self, client):
        body = post(
            client,
            {"title": "T", "author": "A", "publisher": "Secker & Warburg", "id": 99},
        ).get_json()

        assert body["id"] == 1
        assert "publisher" not in body


class TestValidationAppliesToUpdates:
    def test_put_requires_title_and_author(self, client, add_book):
        created = add_book()

        response = client.put(f"/books/{created['id']}", json={"year": 1950})

        assert response.status_code == 400
        assert sorted(response.get_json()["details"]) == ["author", "title"]

    def test_patch_validates_the_fields_it_is_given(self, client, add_book):
        created = add_book()

        response = client.patch(f"/books/{created['id']}", json={"title": "  "})

        assert response.status_code == 400
        assert "title" in response.get_json()["details"]

    def test_a_rejected_update_leaves_the_book_unchanged(self, client, add_book):
        created = add_book()

        client.put(f"/books/{created['id']}", json={"title": ""})

        assert client.get(f"/books/{created['id']}").get_json() == created

    def test_validation_runs_before_the_existence_check(self, client):
        """An invalid body is a client error regardless of the target id."""
        response = client.put("/books/999", json={})

        assert response.status_code == 400
