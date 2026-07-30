"""Input validation on POST, PUT and PATCH."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from bookapi.validation import (
    MAX_AUTHOR_LENGTH,
    MAX_ISBN_LENGTH,
    MAX_TITLE_LENGTH,
    MIN_YEAR,
)


def test_title_is_required(client):
    response = client.post("/books", json={"author": "Chinua Achebe"})

    assert response.status_code == 400
    body = response.get_json()
    assert body["code"] == "validation_error"
    assert body["details"] == {"title": "this field is required"}


def test_author_is_required(client):
    response = client.post("/books", json={"title": "Things Fall Apart"})

    assert response.status_code == 400
    assert response.get_json()["details"] == {"author": "this field is required"}


def test_both_missing_fields_are_reported_together(client):
    response = client.post("/books", json={"year": 1958})

    assert response.status_code == 400
    assert response.get_json()["details"] == {
        "title": "this field is required",
        "author": "this field is required",
    }


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_blank_title_is_rejected(client, blank):
    response = client.post("/books", json={"title": blank, "author": "Anon"})

    assert response.status_code == 400
    assert response.get_json()["details"] == {"title": "must not be empty"}


@pytest.mark.parametrize("value", [123, 4.5, True, [], {}, ["a"]])
def test_non_string_title_is_rejected(client, value):
    response = client.post("/books", json={"title": value, "author": "Anon"})

    assert response.status_code == 400
    assert response.get_json()["details"] == {"title": "must be a string"}


def test_null_title_is_reported_as_missing(client):
    response = client.post("/books", json={"title": None, "author": "Anon"})

    assert response.status_code == 400
    assert response.get_json()["details"] == {"title": "this field is required"}


# The limits are written out rather than imported, so that changing a constant in
# bookapi.validation without updating the README's field table fails the suite.
@pytest.mark.parametrize(("field", "limit"), [("title", 255), ("author", 255)])
def test_text_length_limit_is_the_documented_one(client, field, limit):
    payload = {"title": "T", "author": "A", field: "x" * (limit + 1)}
    response = client.post("/books", json=payload)

    assert response.status_code == 400
    assert response.get_json()["details"] == {
        field: f"must be at most {limit} characters"
    }

    payload[field] = "x" * limit
    assert client.post("/books", json=payload).status_code == 201


def test_isbn_length_limit_is_the_documented_one(client):
    payload = {"title": "T", "author": "A", "isbn": "9" * 33}
    response = client.post("/books", json=payload)

    assert response.status_code == 400
    assert response.get_json()["details"] == {"isbn": "must be at most 32 characters"}

    payload["isbn"] = "9" * 32
    assert client.post("/books", json=payload).status_code == 201


def test_the_constants_match_the_documented_limits(client):
    """Guards the README field table against a silent constant change."""
    assert (MAX_TITLE_LENGTH, MAX_AUTHOR_LENGTH, MAX_ISBN_LENGTH) == (255, 255, 32)
    assert MIN_YEAR == -4000


@pytest.mark.parametrize("value", ["not-a-year", 1958.5, True, [], {"y": 1}])
def test_non_integer_year_is_rejected(client, value):
    response = client.post(
        "/books", json={"title": "T", "author": "A", "year": value}
    )

    assert response.status_code == 400
    assert "year" in response.get_json()["details"]


@pytest.mark.parametrize("value", [-9999, 99999])
def test_out_of_range_year_is_rejected(client, value):
    response = client.post(
        "/books", json={"title": "T", "author": "A", "year": value}
    )

    assert response.status_code == 400
    assert "must be between" in response.get_json()["details"]["year"]


@pytest.mark.parametrize(
    ("sent", "stored"),
    [(1958, 1958), ("1958", 1958), (1958.0, 1958), (None, None), ("", None)],
)
def test_year_is_coerced_to_an_integer_or_null(client, sent, stored):
    response = client.post(
        "/books", json={"title": "T", "author": "A", "year": sent}
    )

    assert response.status_code == 201
    assert response.get_json()["year"] == stored


def test_the_future_year_window_is_ten_years(client):
    """Derived from the calendar, not from FUTURE_YEAR_ALLOWANCE, so shrinking or
    widening that constant fails here instead of silently redefining the API."""
    this_year = datetime.now(timezone.utc).year

    def post(year):
        return client.post(
            "/books", json={"title": "T", "author": "A", "year": year}
        ).status_code

    assert post(this_year) == 201
    assert post(this_year + 10) == 201
    assert post(this_year + 11) == 400


def test_the_earliest_accepted_year_is_minus_4000(client):
    def post(year):
        return client.post(
            "/books", json={"title": "T", "author": "A", "year": year}
        ).status_code

    assert post(-4000) == 201
    assert post(-4001) == 400


def test_non_string_isbn_is_rejected(client):
    response = client.post(
        "/books", json={"title": "T", "author": "A", "isbn": 9780385474542}
    )

    assert response.status_code == 400
    assert response.get_json()["details"] == {"isbn": "must be a string"}


@pytest.mark.parametrize("blank", ["", "  "])
def test_blank_isbn_becomes_null(client, blank):
    response = client.post(
        "/books", json={"title": "T", "author": "A", "isbn": blank}
    )

    assert response.status_code == 201
    assert response.get_json()["isbn"] is None


def test_isbn_whitespace_is_normalised(client):
    response = client.post(
        "/books", json={"title": "T", "author": "A", "isbn": " 978 0385   474542 "}
    )

    assert response.status_code == 201
    assert response.get_json()["isbn"] == "978 0385 474542"


def test_unknown_fields_are_rejected(client):
    response = client.post(
        "/books", json={"title": "T", "author": "A", "publisher": "Heinemann"}
    )

    assert response.status_code == 400
    assert response.get_json()["details"] == {"publisher": "unknown field"}


def test_server_managed_fields_are_ignored_so_a_get_can_be_put_back(client, book):
    edited = dict(book, title="Second Edition")

    response = client.put(f"/books/{book['id']}", json=edited)

    assert response.status_code == 200
    updated = response.get_json()
    assert updated["title"] == "Second Edition"
    assert updated["id"] == book["id"]
    assert updated["created_at"] == book["created_at"]


def test_client_supplied_id_cannot_override_the_real_one(client):
    response = client.post("/books", json={"id": 999, "title": "T", "author": "A"})

    assert response.status_code == 201
    assert response.get_json()["id"] != 999
    assert client.get("/books/999").status_code == 404


def test_put_requires_the_full_representation(client, book):
    response = client.put(f"/books/{book['id']}", json={"year": 1994})

    assert response.status_code == 400
    details = response.get_json()["details"]
    assert details == {
        "title": "this field is required",
        "author": "this field is required",
    }


def test_patch_validates_the_fields_it_is_given(client, book):
    response = client.patch(f"/books/{book['id']}", json={"title": "  "})

    assert response.status_code == 400
    assert response.get_json()["details"] == {"title": "must not be empty"}


def test_failed_validation_does_not_change_stored_data(client, book):
    client.put(f"/books/{book['id']}", json={"title": "", "author": ""})

    assert client.get(f"/books/{book['id']}").get_json() == book


@pytest.mark.parametrize(
    ("label", "title"),
    [
        ("a lone NUL", "\x00"),
        ("NUL between spaces", " \x00 "),
        ("embedded NUL", "Ti\x00tle"),
        ("internal newline", "Ti\ntle"),
        ("internal tab", "Ti\ttle"),
        ("DEL", "Title\x7f"),
    ],
)
def test_control_characters_are_rejected(client, label, title):
    """A NUL survives str.strip(), and SQLite's trim() calls it non-empty even
    though length() calls it empty - so a book with a blank title used to be
    creatable.  Rejecting control characters closes that off."""
    response = client.post("/books", json={"title": title, "author": "A"})

    assert response.status_code == 400, label
    assert response.get_json()["details"] == {
        "title": "must not contain control characters"
    }


def test_control_characters_are_rejected_in_isbn(client):
    response = client.post(
        "/books", json={"title": "T", "author": "A", "isbn": "978\x00123"}
    )

    assert response.status_code == 400
    assert response.get_json()["details"] == {
        "isbn": "must not contain control characters"
    }


@pytest.mark.parametrize(
    "year",
    [
        "1_9_5_8",  # int() accepts underscore separators
        "\u0661\u0669\u0665\u0668",  # Arabic-Indic digits for 1958
        "1958\u200b",  # trailing zero-width space
        "0x7aa",
        "1e3",
    ],
)
def test_year_strings_must_be_plain_ascii_digits(client, year):
    """``int()`` on its own is far more permissive than the documented contract."""
    response = client.post("/books", json={"title": "T", "author": "A", "year": year})

    assert response.status_code == 400
    assert response.get_json()["details"] == {"year": "must be an integer"}


def test_validation_errors_are_reported_for_every_bad_field_at_once(client):
    response = client.post(
        "/books", json={"title": "", "author": 5, "year": "soon", "isbn": []}
    )

    assert response.status_code == 400
    assert set(response.get_json()["details"]) == {"title", "author", "year", "isbn"}
