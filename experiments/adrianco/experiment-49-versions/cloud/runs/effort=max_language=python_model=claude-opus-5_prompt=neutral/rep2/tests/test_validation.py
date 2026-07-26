"""Tests for payload and query-string validation."""

from __future__ import annotations

import pytest

from book_api.utils import current_year
from book_api.validators import (
    has_isbn_shape,
    has_valid_isbn_checksum,
    normalize_isbn,
)


# ----------------------------------------------------------------------
# Required fields
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "payload, missing",
    [
        ({}, {"title", "author"}),
        ({"title": "Dune"}, {"author"}),
        ({"author": "Frank Herbert"}, {"title"}),
    ],
)
def test_title_and_author_are_required(client, payload, missing):
    response = client.post("/books", json=payload)

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "validation_error"
    assert set(body["details"]) == missing


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_blank_titles_are_rejected(client, blank):
    response = client.post("/books", json={"title": blank, "author": "Frank Herbert"})

    assert response.status_code == 400
    assert response.get_json()["details"]["title"] == "Must not be empty."


@pytest.mark.parametrize("value", [42, 3.5, True, ["Dune"], {"name": "Dune"}])
def test_non_string_titles_are_rejected(client, value):
    response = client.post("/books", json={"title": value, "author": "Frank Herbert"})

    assert response.status_code == 400
    assert response.get_json()["details"]["title"] == "Must be a string."


def test_overlong_values_are_rejected(client):
    response = client.post("/books", json={"title": "x" * 513, "author": "Frank Herbert"})

    assert response.status_code == 400
    assert "at most 512" in response.get_json()["details"]["title"]


def test_every_problem_is_reported_at_once(client):
    response = client.post("/books", json={"title": "", "author": 7, "year": "soon", "isbn": "nope"})

    details = response.get_json()["details"]
    assert set(details) == {"title", "author", "year", "isbn"}


def test_nothing_is_stored_when_validation_fails(client):
    client.post("/books", json={"author": "Frank Herbert"})

    assert client.get("/books").get_json() == []


# ----------------------------------------------------------------------
# Body shape
# ----------------------------------------------------------------------
@pytest.mark.parametrize("body", ["[]", '"Dune"', "42", "null"])
def test_a_json_body_that_is_not_an_object_is_rejected(client, body):
    response = client.post("/books", data=body, content_type="application/json")

    assert response.status_code == 400
    assert response.get_json()["error"] == "validation_error"


def test_malformed_json_is_rejected(client):
    response = client.post("/books", data="{not json", content_type="application/json")

    assert response.status_code == 400
    assert "body" in response.get_json()["details"]


def test_an_empty_body_is_rejected(client):
    response = client.post("/books", data="", content_type="application/json")

    assert response.status_code == 400


# ----------------------------------------------------------------------
# year
# ----------------------------------------------------------------------
@pytest.mark.parametrize("value", ["soon", "19x5", True, [1965], {"y": 1965}, 1965.5])
def test_invalid_years_are_rejected(client, value):
    response = client.post("/books", json={"title": "Dune", "author": "Frank Herbert", "year": value})

    assert response.status_code == 400
    assert "year" in response.get_json()["details"]


@pytest.mark.parametrize("value", [0, -5])
def test_years_below_the_minimum_are_rejected(client, value):
    response = client.post("/books", json={"title": "Dune", "author": "Frank Herbert", "year": value})

    assert response.status_code == 400


def test_years_far_in_the_future_are_rejected(client):
    response = client.post(
        "/books", json={"title": "Dune", "author": "Frank Herbert", "year": current_year() + 2}
    )

    assert response.status_code == 400
    assert "year" in response.get_json()["details"]


def test_next_years_publications_are_accepted(client):
    response = client.post(
        "/books", json={"title": "Dune", "author": "Frank Herbert", "year": current_year() + 1}
    )

    assert response.status_code == 201


@pytest.mark.parametrize("value, expected", [("1965", 1965), (1965.0, 1965), (" 1965 ", 1965)])
def test_numeric_year_representations_are_coerced(client, value, expected):
    response = client.post(
        "/books", json={"title": "Dune", "author": "Frank Herbert", "year": value}
    )

    assert response.status_code == 201
    assert response.get_json()["year"] == expected


# ----------------------------------------------------------------------
# isbn
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "value",
    ["not-an-isbn", "123", "97804410135931", "978044101359X", 9780441013593],
)
def test_invalid_isbns_are_rejected(client, value):
    response = client.post("/books", json={"title": "Dune", "author": "Frank Herbert", "isbn": value})

    assert response.status_code == 400
    assert "isbn" in response.get_json()["details"]


@pytest.mark.parametrize(
    "value", ["9780441013593", "978-0-441-01359-3", "0441013597", "044101359X", "0 441 01359 7"]
)
def test_well_formed_isbns_are_accepted(client, value):
    response = client.post("/books", json={"title": "Dune", "author": "Frank Herbert", "isbn": value})

    assert response.status_code == 201
    assert response.get_json()["isbn"] == value.strip()


def test_an_empty_isbn_is_stored_as_null(client):
    response = client.post("/books", json={"title": "Dune", "author": "Frank Herbert", "isbn": "  "})

    assert response.status_code == 201
    assert response.get_json()["isbn"] is None


def test_differently_formatted_isbns_are_the_same_isbn(client):
    client.post("/books", json={"title": "Dune", "author": "Frank Herbert", "isbn": "9780441013593"})

    duplicate = client.post(
        "/books", json={"title": "Dune", "author": "Frank Herbert", "isbn": "978 0 441 01359 3"}
    )

    assert duplicate.status_code == 409


def test_checksum_validation_is_off_by_default(client):
    response = client.post("/books", json={"title": "Dune", "author": "Frank Herbert", "isbn": "9780441013594"})

    assert response.status_code == 201


def test_checksum_validation_can_be_switched_on():
    from book_api import create_app

    app = create_app({"DATABASE": ":memory:", "TESTING": True, "STRICT_ISBN_CHECKSUM": True})
    client = app.test_client()

    rejected = client.post("/books", json={"title": "Dune", "author": "F. H.", "isbn": "9780441013594"})
    accepted = client.post("/books", json={"title": "Dune", "author": "F. H.", "isbn": "9780441013593"})

    assert rejected.status_code == 400
    assert accepted.status_code == 201


@pytest.mark.parametrize(
    "raw, expected", [("978-0-441-01359-3", "9780441013593"), (" 044101359x ", "044101359X")]
)
def test_normalize_isbn(raw, expected):
    assert normalize_isbn(raw.strip()) == expected


@pytest.mark.parametrize("value, valid", [("9780441013593", True), ("044101359X", True), ("12345", False)])
def test_has_isbn_shape(value, valid):
    assert has_isbn_shape(value) is valid


@pytest.mark.parametrize(
    "value, valid",
    [
        ("9780441013593", True),  # ISBN-13 with a correct check digit
        ("9780441013594", False),
        ("0441013597", True),  # ISBN-10
        ("0441013598", False),
        ("080442957X", True),  # ISBN-10 whose check digit is X
    ],
)
def test_has_valid_isbn_checksum(value, valid):
    assert has_valid_isbn_checksum(value) is valid


# ----------------------------------------------------------------------
# Query string
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "query, field",
    [
        ("limit=abc", "limit"),
        ("limit=0", "limit"),
        ("limit=-1", "limit"),
        ("limit=100000", "limit"),
        ("offset=-1", "offset"),
        ("offset=x", "offset"),
        ("year=recent", "year"),
        ("sort=publisher", "sort"),
        ("sort=-publisher", "sort"),
    ],
)
def test_invalid_query_parameters_are_rejected(client, query, field):
    response = client.get("/books?" + query)

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "validation_error"
    assert field in body["details"]


def test_unknown_query_parameters_are_ignored(client, library):
    response = client.get("/books?colour=blue")

    assert response.status_code == 200
    assert len(response.get_json()) == len(library)


# ----------------------------------------------------------------------
# Values SQLite cannot represent
# ----------------------------------------------------------------------
HUGE = 10 ** 20  # larger than the signed 64-bit integer SQLite stores


@pytest.mark.parametrize("query", ["year={}".format(HUGE), "offset={}".format(HUGE)])
def test_query_integers_too_large_for_sqlite_are_rejected(client, query):
    response = client.get("/books?" + query)

    assert response.status_code == 400
    assert response.get_json()["error"] == "validation_error"


@pytest.mark.parametrize("method", ["get", "delete"])
def test_an_id_too_large_for_sqlite_is_simply_not_found(client, method):
    response = getattr(client, method)("/books/{}".format(HUGE))

    assert response.status_code == 404
    assert response.get_json()["error"] == "not_found"


@pytest.mark.parametrize("method", ["put", "patch"])
def test_writing_to_an_id_too_large_for_sqlite_is_not_found(client, method):
    response = getattr(client, method)(
        "/books/{}".format(HUGE), json={"title": "Ghost", "author": "Nobody"}
    )

    assert response.status_code == 404


def test_null_bytes_are_rejected(client):
    response = client.post("/books", json={"title": "Du\x00ne", "author": "Frank Herbert"})

    assert response.status_code == 400
    assert response.get_json()["details"]["title"] == "Must not contain null bytes."


#: Longer than the 4300 digits CPython is willing to convert with int().
ABSURDLY_LONG_NUMBER = "9" * 4301


@pytest.mark.parametrize("field", ["year", "limit", "offset"])
def test_absurdly_long_query_numbers_are_rejected(client, field):
    response = client.get("/books?{}={}".format(field, ABSURDLY_LONG_NUMBER))

    assert response.status_code == 400
    assert field in response.get_json()["details"]


def test_an_absurdly_long_year_string_is_rejected(client):
    response = client.post(
        "/books", json={"title": "Dune", "author": "Frank Herbert", "year": ABSURDLY_LONG_NUMBER}
    )

    assert response.status_code == 400
    assert "year" in response.get_json()["details"]


@pytest.mark.parametrize("field", ["title", "author"])
def test_unpaired_surrogates_are_rejected(client, field):
    payload = {"title": "Dune", "author": "Frank Herbert"}
    payload[field] = "\\ud800"
    body = '{{"title": "{}", "author": "{}"}}'.format(payload["title"], payload["author"])

    response = client.post("/books", data=body, content_type="application/json")

    assert response.status_code == 400
    assert response.get_json()["details"][field] == "Must be valid UTF-8 text."


@pytest.mark.parametrize("value", ["٩٧٨٠٤٤١٠١٣٥٩٣", "９７８０４４１０１３５９３"])
def test_non_ascii_digits_are_not_isbns(client, value):
    """Arabic-Indic and fullwidth digits must not slip past the ISBN rules."""
    response = client.post("/books", json={"title": "Dune", "author": "F. H.", "isbn": value})

    assert response.status_code == 400
    assert "isbn" in response.get_json()["details"]


def test_a_non_ascii_isbn_cannot_shadow_an_existing_one(client, create_book):
    create_book(isbn="978-0-441-01359-3")

    response = client.post(
        "/books", json={"title": "Copy", "author": "F. H.", "isbn": "٩٧٨٠٤٤١٠١٣٥٩٣"}
    )

    assert response.status_code == 400  # rejected outright, so uniqueness holds
    assert len(client.get("/books").get_json()) == 1


@pytest.mark.parametrize("value", ["١٩٦٥", "１９６５"])
def test_non_ascii_digits_are_not_years(client, value):
    response = client.post("/books", json={"title": "Dune", "author": "F. H.", "year": value})

    assert response.status_code == 400
    assert response.get_json()["details"]["year"] == "Must be an integer."


def test_an_oversized_body_is_refused(client):
    response = client.post(
        "/books",
        data=b'{"title": "' + b"x" * (2 * 1024 * 1024) + b'", "author": "a"}',
        content_type="application/json",
    )

    assert response.status_code == 413
    # Python renamed this status's phrase in 3.13 (RFC 9110), so accept both.
    assert response.get_json()["error"] in {"content_too_large", "request_entity_too_large"}
