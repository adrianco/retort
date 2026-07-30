"""The five required endpoints, end to end."""

from __future__ import annotations

from .samples import SAMPLE_BOOKS


def test_create_book_returns_201_with_location_and_body(client):
    response = client.post("/books", json=SAMPLE_BOOKS[0])

    assert response.status_code == 201
    assert response.mimetype == "application/json"

    book = response.get_json()
    assert book["id"] > 0
    assert book["title"] == "Things Fall Apart"
    assert book["author"] == "Chinua Achebe"
    assert book["year"] == 1958
    assert book["isbn"] == "978-0-385-47454-2"
    assert book["created_at"] == book["updated_at"]
    assert response.headers["Location"].endswith(f"/books/{book['id']}")


def test_create_book_accepts_only_the_required_fields(client):
    response = client.post("/books", json={"title": "Untitled", "author": "Anon"})

    assert response.status_code == 201
    book = response.get_json()
    assert book["year"] is None
    assert book["isbn"] is None


def test_create_book_trims_surrounding_whitespace(client):
    response = client.post(
        "/books", json={"title": "  Dune  ", "author": "\tFrank Herbert\n"}
    )

    assert response.status_code == 201
    book = response.get_json()
    assert book["title"] == "Dune"
    assert book["author"] == "Frank Herbert"


def test_ids_are_unique_across_books(client):
    ids = {
        client.post("/books", json=payload).get_json()["id"]
        for payload in SAMPLE_BOOKS
    }
    assert len(ids) == len(SAMPLE_BOOKS)


def test_list_books_returns_every_book(client, library):
    response = client.get("/books")

    assert response.status_code == 200
    books = response.get_json()
    assert isinstance(books, list)
    assert len(books) == 3
    assert [b["title"] for b in books] == [b["title"] for b in library]
    assert response.headers["X-Total-Count"] == "3"


def test_list_books_is_empty_before_anything_is_created(client):
    response = client.get("/books")

    assert response.status_code == 200
    assert response.get_json() == []
    assert response.headers["X-Total-Count"] == "0"


def test_get_book_by_id(client, book):
    response = client.get(f"/books/{book['id']}")

    assert response.status_code == 200
    assert response.get_json() == book


def test_get_missing_book_returns_404_json(client):
    response = client.get("/books/424242")

    assert response.status_code == 404
    body = response.get_json()
    assert body["code"] == "not_found"
    assert "424242" in body["error"]


def test_put_replaces_the_whole_book(client, book):
    response = client.put(
        f"/books/{book['id']}",
        json={"title": "Things Fall Apart", "author": "C. Achebe", "year": 1994},
    )

    assert response.status_code == 200
    updated = response.get_json()
    assert updated["id"] == book["id"]
    assert updated["author"] == "C. Achebe"
    assert updated["year"] == 1994
    # isbn was omitted, so a full replacement clears it.
    assert updated["isbn"] is None
    assert updated["created_at"] == book["created_at"]
    assert updated["updated_at"] >= book["updated_at"]


def test_put_change_is_persisted(client, book):
    client.put(f"/books/{book['id']}", json={"title": "Revised", "author": "Achebe"})

    assert client.get(f"/books/{book['id']}").get_json()["title"] == "Revised"


def test_repeating_the_same_put_still_succeeds(client, book):
    """A replacement that changes nothing must not be mistaken for a missing row.

    The 404 for an unknown id comes from ``cursor.rowcount == 0``, so this pins
    down that SQLite counts a no-op UPDATE of an existing row as one change.
    """
    payload = {"title": book["title"], "author": book["author"], "year": book["year"]}

    assert client.put(f"/books/{book['id']}", json=payload).status_code == 200
    assert client.put(f"/books/{book['id']}", json=payload).status_code == 200


def test_put_missing_book_returns_404(client):
    response = client.put("/books/424242", json={"title": "T", "author": "A"})

    assert response.status_code == 404
    assert response.get_json()["code"] == "not_found"


def test_patch_updates_only_the_supplied_fields(client, book):
    response = client.patch(f"/books/{book['id']}", json={"year": 2001})

    assert response.status_code == 200
    updated = response.get_json()
    assert updated["year"] == 2001
    assert updated["title"] == book["title"]
    assert updated["isbn"] == book["isbn"]


def test_patch_with_no_fields_is_rejected(client, book):
    response = client.patch(f"/books/{book['id']}", json={})

    assert response.status_code == 400
    assert response.get_json()["code"] == "validation_error"


def test_delete_book_returns_204_and_removes_it(client, book):
    response = client.delete(f"/books/{book['id']}")

    assert response.status_code == 204
    assert response.data == b""
    assert client.get(f"/books/{book['id']}").status_code == 404
    assert client.get("/books").get_json() == []


def test_delete_is_not_idempotent_in_status(client, book):
    assert client.delete(f"/books/{book['id']}").status_code == 204
    assert client.delete(f"/books/{book['id']}").status_code == 404


def test_delete_leaves_other_books_alone(client, library):
    client.delete(f"/books/{library[1]['id']}")

    remaining = client.get("/books").get_json()
    assert [b["id"] for b in remaining] == [library[0]["id"], library[2]["id"]]
