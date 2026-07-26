"""Input-validation tests: title and author are required, year/isbn are checked."""

import pytest


def _fields_in_error(resp):
    return {err["loc"][-1] for err in resp.json()["detail"]}


@pytest.mark.parametrize(
    "payload, missing",
    [
        ({"author": "Someone"}, "title"),
        ({"title": "Something"}, "author"),
        ({}, "title"),
    ],
)
def test_missing_required_fields_rejected(client, payload, missing):
    resp = client.post("/books", json=payload)

    assert resp.status_code == 422
    assert missing in _fields_in_error(resp)


@pytest.mark.parametrize("blank", ["", "   "])
@pytest.mark.parametrize("field", ["title", "author"])
def test_blank_required_fields_rejected(client, field, blank):
    payload = {"title": "T", "author": "A", field: blank}

    resp = client.post("/books", json=payload)

    assert resp.status_code == 422
    assert field in _fields_in_error(resp)


def test_required_fields_are_whitespace_trimmed(client):
    resp = client.post("/books", json={"title": "  Dune  ", "author": " Herbert "})

    assert resp.status_code == 201
    assert resp.json()["title"] == "Dune"
    assert resp.json()["author"] == "Herbert"


@pytest.mark.parametrize("year", [42, 3000, "not-a-year"])
def test_invalid_year_rejected(client, year):
    resp = client.post("/books", json={"title": "T", "author": "A", "year": year})

    assert resp.status_code == 422
    assert "year" in _fields_in_error(resp)


@pytest.mark.parametrize("isbn", ["12345", "abcdefghij", "9780441478125123"])
def test_invalid_isbn_rejected(client, isbn):
    resp = client.post("/books", json={"title": "T", "author": "A", "isbn": isbn})

    assert resp.status_code == 422
    assert "isbn" in _fields_in_error(resp)


@pytest.mark.parametrize("isbn", ["9780441478125", "0-441-47812-3", "156881111X"])
def test_valid_isbn_formats_accepted(client, isbn):
    resp = client.post("/books", json={"title": "T", "author": "A", "isbn": isbn})

    assert resp.status_code == 201
    assert resp.json()["isbn"] == isbn


def test_empty_isbn_stored_as_null_and_does_not_collide(client):
    first = client.post("/books", json={"title": "A", "author": "X", "isbn": ""})
    second = client.post("/books", json={"title": "B", "author": "Y", "isbn": ""})

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["isbn"] is None


def test_unknown_fields_rejected(client):
    resp = client.post(
        "/books", json={"title": "T", "author": "A", "publisher": "Ace"}
    )

    assert resp.status_code == 422


def test_update_validates_the_same_way(client, sample_book):
    book_id = client.post("/books", json=sample_book).json()["id"]

    resp = client.put(f"/books/{book_id}", json={"author": "Only Author"})

    assert resp.status_code == 422
    assert "title" in _fields_in_error(resp)


def test_non_integer_id_rejected(client):
    assert client.get("/books/not-an-id").status_code == 422
