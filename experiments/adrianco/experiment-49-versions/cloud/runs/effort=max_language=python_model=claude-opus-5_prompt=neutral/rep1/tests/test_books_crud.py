"""End-to-end tests for the CRUD lifecycle of a book."""

from sample_data import SAMPLE_BOOK


# --------------------------------------------------------------------------- #
# POST /books
# --------------------------------------------------------------------------- #


def test_create_book_returns_201_and_the_stored_book(client):
    response = client.post("/books", json=SAMPLE_BOOK)

    assert response.status_code == 201
    book = response.get_json()
    assert book["id"] > 0
    assert book["title"] == SAMPLE_BOOK["title"]
    assert book["author"] == SAMPLE_BOOK["author"]
    assert book["year"] == SAMPLE_BOOK["year"]
    assert book["isbn"] == SAMPLE_BOOK["isbn"]
    assert book["created_at"] and book["updated_at"]


def test_create_book_sets_location_header(client):
    response = client.post("/books", json=SAMPLE_BOOK)

    book_id = response.get_json()["id"]
    assert response.headers["Location"].endswith(f"/books/{book_id}")


def test_create_book_only_requires_title_and_author(client):
    response = client.post("/books", json={"title": "Dune", "author": "Herbert"})

    assert response.status_code == 201
    book = response.get_json()
    assert book["year"] is None
    assert book["isbn"] is None


def test_ids_are_unique_per_book(make_book):
    first, second = make_book(), make_book()

    assert first["id"] != second["id"]


# --------------------------------------------------------------------------- #
# GET /books and GET /books/{id}
# --------------------------------------------------------------------------- #


def test_list_books_is_empty_initially(client):
    response = client.get("/books")

    assert response.status_code == 200
    assert response.get_json() == []


def test_list_books_returns_every_book_in_insertion_order(client, make_book):
    created = [make_book(title=f"Book {index}") for index in range(3)]

    response = client.get("/books")

    assert response.status_code == 200
    assert [book["id"] for book in response.get_json()] == [
        book["id"] for book in created
    ]
    assert response.headers["X-Total-Count"] == "3"


def test_get_book_by_id(client, make_book):
    created = make_book()

    response = client.get(f"/books/{created['id']}")

    assert response.status_code == 200
    assert response.get_json() == created


def test_get_unknown_book_returns_404_json(client):
    response = client.get("/books/9999")

    assert response.status_code == 404
    assert response.headers["Content-Type"].startswith("application/json")
    assert "9999" in response.get_json()["error"]


def test_get_book_with_non_numeric_id_returns_404(client):
    assert client.get("/books/not-a-number").status_code == 404


# --------------------------------------------------------------------------- #
# PUT /books/{id}
# --------------------------------------------------------------------------- #


def test_put_replaces_all_fields(client, make_book):
    created = make_book()

    response = client.put(
        f"/books/{created['id']}",
        json={
            "title": "The Silmarillion",
            "author": "J.R.R. Tolkien",
            "year": 1977,
            "isbn": "9780261102736",
        },
    )

    assert response.status_code == 200
    updated = response.get_json()
    assert updated["id"] == created["id"]
    assert updated["title"] == "The Silmarillion"
    assert updated["year"] == 1977
    assert updated["isbn"] == "9780261102736"
    assert updated["created_at"] == created["created_at"]


def test_put_accepts_a_partial_body(client, make_book):
    created = make_book()

    response = client.put(f"/books/{created['id']}", json={"title": "Updated"})

    assert response.status_code == 200
    updated = response.get_json()
    assert updated["title"] == "Updated"
    assert updated["author"] == created["author"]
    assert updated["year"] == created["year"]


def test_patch_updates_a_single_field(client, make_book):
    created = make_book()

    response = client.patch(f"/books/{created['id']}", json={"year": 1951})

    assert response.status_code == 200
    assert response.get_json()["year"] == 1951


def test_update_refreshes_updated_at_but_not_created_at(client, make_book):
    created = make_book()

    updated = client.put(
        f"/books/{created['id']}", json={"title": "Updated"}
    ).get_json()

    assert updated["created_at"] == created["created_at"]
    # ISO-8601 UTC strings of a fixed width sort chronologically.
    assert updated["updated_at"] >= created["updated_at"]


def test_update_is_persisted(client, make_book):
    created = make_book()

    client.put(f"/books/{created['id']}", json={"author": "Someone Else"})

    assert client.get(f"/books/{created['id']}").get_json()["author"] == (
        "Someone Else"
    )


def test_explicit_null_clears_optional_fields(client, make_book):
    created = make_book()

    response = client.put(
        f"/books/{created['id']}", json={"year": None, "isbn": None}
    )

    assert response.status_code == 200
    assert response.get_json()["year"] is None
    assert response.get_json()["isbn"] is None


def test_update_unknown_book_returns_404(client):
    response = client.put("/books/9999", json={"title": "Ghost"})

    assert response.status_code == 404
    assert "error" in response.get_json()


# --------------------------------------------------------------------------- #
# DELETE /books/{id}
# --------------------------------------------------------------------------- #


def test_delete_returns_204_and_removes_the_book(client, make_book):
    created = make_book()

    response = client.delete(f"/books/{created['id']}")

    assert response.status_code == 204
    assert response.get_data() == b""
    assert client.get(f"/books/{created['id']}").status_code == 404
    assert client.get("/books").get_json() == []


def test_delete_unknown_book_returns_404(client):
    response = client.delete("/books/9999")

    assert response.status_code == 404
    assert "error" in response.get_json()


def test_delete_is_not_repeatable(client, make_book):
    created = make_book()

    assert client.delete(f"/books/{created['id']}").status_code == 204
    assert client.delete(f"/books/{created['id']}").status_code == 404


def test_delete_leaves_other_books_alone(client, make_book):
    doomed, survivor = make_book(title="Doomed"), make_book(title="Survivor")

    client.delete(f"/books/{doomed['id']}")

    remaining = client.get("/books").get_json()
    assert [book["id"] for book in remaining] == [survivor["id"]]
