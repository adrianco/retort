"""Input validation and request-shape errors."""

from __future__ import annotations

import json

import pytest

VALID = {"title": "Solaris", "author": "Stanisław Lem"}


def _fields(response):
    return response.get_json()["error"].get("fields", {})


@pytest.mark.parametrize(
    "payload, bad_field",
    [
        ({"author": "A"}, "title"),
        ({"title": "T"}, "author"),
        ({"title": "", "author": "A"}, "title"),
        ({"title": "   ", "author": "A"}, "title"),
        ({"title": "T", "author": ""}, "author"),
        ({"title": None, "author": "A"}, "title"),
        ({"title": "T", "author": None}, "author"),
        ({"title": 42, "author": "A"}, "title"),
        ({"title": "T", "author": ["A", "B"]}, "author"),
        ({"title": "T" * 501, "author": "A"}, "title"),
        ({"title": "T", "author": "A" * 256}, "author"),
        ({"title": "T", "author": "A", "year": "not a year"}, "year"),
        ({"title": "T", "author": "A", "year": 1969.5}, "year"),
        ({"title": "T", "author": "A", "year": True}, "year"),
        ({"title": "T", "author": "A", "year": 0}, "year"),
        ({"title": "T", "author": "A", "year": -5}, "year"),
        ({"title": "T", "author": "A", "year": 9999}, "year"),
        ({"title": "T", "author": "A", "isbn": 12345}, "isbn"),
        ({"title": "T", "author": "A", "isbn": "x" * 65}, "isbn"),
        ({"title": "T", "author": "A", "publisher": "Faber"}, "publisher"),
    ],
)
def test_invalid_payloads_are_rejected(client, payload, bad_field):
    response = client.post("/books", json=payload)

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"]["code"] == "validation_error"
    assert bad_field in body["error"]["fields"]
    assert client.get("/books").get_json() == [], "nothing should have been stored"


def test_all_problems_are_reported_at_once(client):
    response = client.post("/books", json={"year": 12345, "isbn": 9})

    assert response.status_code == 400
    assert set(_fields(response)) == {"title", "author", "year", "isbn"}


def test_validation_also_applies_to_put(client, created_book):
    response = client.put(f"/books/{created_book['id']}", json={"author": "A"})

    assert response.status_code == 400
    assert "title" in _fields(response)
    # The stored book is untouched.
    unchanged = client.get(f"/books/{created_book['id']}").get_json()
    assert unchanged == created_book


def test_body_id_must_match_the_url(client, created_book):
    response = client.put(
        f"/books/{created_book['id']}", json=dict(VALID, id=created_book["id"] + 1)
    )

    assert response.status_code == 400
    assert "id" in _fields(response)


@pytest.mark.parametrize(
    "body_id",
    [
        2,  # plain mismatch
        "2",  # mismatch as a string
        True,  # bool: True == 1 must not satisfy book 1
        # str.isdigit() is True for these but int() raises ValueError on them,
        # which used to escape as a 500 instead of a 400.
        "²",  # superscript two
        "₂",  # subscript two
        "፩",  # Ethiopic digit one
        "1_1",  # PEP 515 underscore
        "+1",  # signed
        "abc",
    ],
)
def test_mismatched_body_id_is_a_400_never_a_500(client, created_book, body_id):
    assert created_book["id"] == 1

    response = client.put(f"/books/1", json=dict(VALID, id=body_id))

    assert response.status_code == 400
    assert "id" in _fields(response)


def test_id_mismatch_does_not_hide_the_other_field_errors(client, created_book):
    """One response must still list every problem, not just the id."""
    response = client.put(
        f"/books/{created_book['id']}",
        json={"id": created_book["id"] + 1, "year": "x", "nope": 1},
    )

    assert response.status_code == 400
    assert set(_fields(response)) == {"id", "title", "author", "year", "nope"}


@pytest.mark.parametrize("year", [2020, "2020", " 2020 "])
def test_year_accepts_integers_and_integral_strings(client, year):
    response = client.post("/books", json=dict(VALID, year=year))

    assert response.status_code == 201
    assert response.get_json()["year"] == 2020


@pytest.mark.parametrize(
    "year",
    [
        "2_020",  # int() would read this as 2020 via PEP 515
        "+2020",  # int() would accept the sign
        "٣",  # Arabic-Indic three: int() reads 3
        "²",  # isdigit() True, int() raises
        "20 20",
        "0x7e4",
        "2020.0",
    ],
)
def test_year_rejects_strings_that_are_not_plain_digits(client, year):
    """Silently misparsing a year is worse than refusing it."""
    response = client.post("/books", json=dict(VALID, year=year))

    assert response.status_code == 400
    assert "year" in _fields(response)


def test_blank_isbn_is_stored_as_null_so_it_never_collides(client):
    first = client.post("/books", json=dict(VALID, isbn=""))
    second = client.post("/books", json={"title": "B", "author": "C", "isbn": "   "})

    assert first.status_code == 201
    assert first.get_json()["isbn"] is None
    assert second.status_code == 201, "a blank isbn must not conflict"


def test_duplicate_isbn_returns_409(client):
    client.post("/books", json=dict(VALID, isbn="978-0-15-601219-8"))

    response = client.post(
        "/books", json={"title": "Other", "author": "Other", "isbn": "978-0-15-601219-8"}
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "conflict"


def test_put_cannot_steal_another_books_isbn(client, created_book):
    other = client.post(
        "/books", json={"title": "Other", "author": "Other", "isbn": "111"}
    ).get_json()

    response = client.put(
        f"/books/{other['id']}",
        json={"title": "Other", "author": "Other", "isbn": created_book["isbn"]},
    )

    assert response.status_code == 409


def test_put_may_keep_its_own_isbn(client, created_book):
    response = client.put(
        f"/books/{created_book['id']}",
        json={"title": "New", "author": "New", "isbn": created_book["isbn"]},
    )

    assert response.status_code == 200
    assert response.get_json()["isbn"] == created_book["isbn"]


@pytest.mark.parametrize(
    "content_type",
    ["application/x-www-form-urlencoded", "text/plain", "application/xml", ""],
)
def test_non_json_content_type_returns_415(client, content_type):
    response = client.post("/books", data=json.dumps(VALID), content_type=content_type)

    assert response.status_code == 415
    assert response.get_json()["error"]["code"] == "unsupported_media_type"


@pytest.mark.parametrize(
    "content_type",
    ["application/json", "application/json; charset=utf-8", "application/hal+json"],
)
def test_json_suffix_content_types_are_accepted(client, content_type):
    """RFC 6839 +json suffix types are JSON, so they are honoured."""
    response = client.post("/books", data=json.dumps(VALID), content_type=content_type)

    assert response.status_code == 201


def test_malformed_json_returns_400_not_500(client):
    response = client.post(
        "/books", data="{not json", content_type="application/json"
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_empty_body_returns_400(client):
    response = client.post("/books", data="", content_type="application/json")

    assert response.status_code == 400


@pytest.mark.parametrize("body", ["[]", '"a string"', "42", "null"])
def test_json_that_is_not_an_object_returns_400(client, body):
    response = client.post("/books", data=body, content_type="application/json")

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize(
    "raw, bad_field",
    [
        # JSON allows these escapes; Python decodes them to unpaired surrogates,
        # which SQLite cannot encode. They must be a 400, never a 500.
        ('{"title":"\\ud800","author":"A"}', "title"),
        ('{"title":"T","author":"\\udc00"}', "author"),
        ('{"title":"T","author":"A","isbn":"\\udfff"}', "isbn"),
        ('{"title":"a\\u0000b","author":"A"}', "title"),
        ('{"title":"T","author":"A","isbn":"9\\u000078"}', "isbn"),
    ],
)
def test_text_sqlite_cannot_store_is_rejected_with_400(client, raw, bad_field):
    response = client.post(
        "/books",
        data=raw.encode("utf-8", "surrogatepass"),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert bad_field in _fields(response)
    assert client.get("/books").get_json() == []


@pytest.mark.parametrize(
    "title", ["Emoji \U0001f600", "Naïve", "日本語", "Zoë́", "‮RTL"]
)
def test_legitimate_unicode_is_accepted_and_round_trips(client, title):
    created = client.post("/books", json={"title": title, "author": "A"})

    assert created.status_code == 201
    assert client.get(f"/books/{created.get_json()['id']}").get_json()["title"] == title


def test_oversized_body_returns_413_as_json(client):
    huge = '{"title":"' + "x" * (64 * 1024) + '","author":"A"}'

    response = client.post("/books", data=huge, content_type="application/json")

    assert response.status_code == 413
    assert response.mimetype == "application/json"
    assert response.get_json()["error"]["code"] == "request_entity_too_large"
