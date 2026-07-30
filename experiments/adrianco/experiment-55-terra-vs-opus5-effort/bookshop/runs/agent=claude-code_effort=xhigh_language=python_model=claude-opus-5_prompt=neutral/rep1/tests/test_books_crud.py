"""The CRUD surface: POST/GET/PUT/PATCH/DELETE over /books."""

from __future__ import annotations

from conftest import HUXLEY, ORWELL, ORWELL_2


def test_create_returns_201_with_the_stored_book(client):
    response = client.post("/books", json=ORWELL)

    assert response.status_code == 201
    book = response.get_json()
    assert isinstance(book["id"], int)
    assert book["title"] == ORWELL["title"]
    assert book["author"] == ORWELL["author"]
    assert book["year"] == ORWELL["year"]
    assert book["isbn"] == ORWELL["isbn"]
    assert book["created_at"] == book["updated_at"]
    assert response.headers["Location"] == f"/books/{book['id']}"


def test_create_accepts_a_book_without_optional_fields(client):
    response = client.post("/books", json={"title": "Untitled", "author": "Anon"})

    assert response.status_code == 201
    assert response.get_json()["year"] is None
    assert response.get_json()["isbn"] is None


def test_create_trims_surrounding_whitespace(client):
    book = client.post("/books", json={"title": "  Dune\n", "author": "\tFrank Herbert "})

    assert book.get_json()["title"] == "Dune"
    assert book.get_json()["author"] == "Frank Herbert"


def test_create_normalises_hyphenated_isbn(client):
    book = client.post("/books", json={**ORWELL, "isbn": "978-0-451-52493-5"})

    assert book.get_json()["isbn"] == "9780451524935"


def test_get_returns_a_single_book(client, create_book):
    created = create_book()

    response = client.get(f"/books/{created['id']}")

    assert response.status_code == 200
    assert response.get_json() == created


def test_get_unknown_book_returns_404(client):
    response = client.get("/books/4242")

    assert response.status_code == 404
    assert response.get_json()["error"] == "not_found"
    assert "4242" in response.get_json()["message"]


def test_list_returns_all_books_in_insertion_order(client, create_book):
    first = create_book(ORWELL)
    second = create_book(HUXLEY)

    response = client.get("/books")

    assert response.status_code == 200
    assert [book["id"] for book in response.get_json()] == [first["id"], second["id"]]
    assert response.headers["X-Total-Count"] == "2"


def test_list_is_empty_before_anything_is_created(client):
    assert client.get("/books").get_json() == []


def test_list_filters_by_author(client, create_book):
    create_book(ORWELL)
    create_book(HUXLEY)
    create_book(ORWELL_2)

    response = client.get("/books?author=George Orwell")

    assert response.status_code == 200
    titles = [book["title"] for book in response.get_json()]
    assert titles == ["Nineteen Eighty-Four", "Animal Farm"]
    assert response.headers["X-Total-Count"] == "2"


def test_author_filter_ignores_case_and_padding(client, create_book):
    create_book(ORWELL)

    response = client.get("/books?author=  george ORWELL  ")

    assert [book["title"] for book in response.get_json()] == [ORWELL["title"]]


def test_author_filter_with_no_matches_returns_empty_list(client, create_book):
    create_book(ORWELL)

    response = client.get("/books?author=Ursula K. Le Guin")

    assert response.status_code == 200
    assert response.get_json() == []


def test_blank_author_filter_is_ignored(client, create_book):
    create_book(ORWELL)
    create_book(HUXLEY)

    assert len(client.get("/books?author=").get_json()) == 2
    assert len(client.get("/books?author=%20").get_json()) == 2


def test_list_supports_limit_and_offset(client, create_book):
    create_book(ORWELL)
    second = create_book(HUXLEY)

    response = client.get("/books?limit=1&offset=1")

    assert [book["id"] for book in response.get_json()] == [second["id"]]
    # The header reports the full match count, not the page size.
    assert response.headers["X-Total-Count"] == "2"


def test_put_replaces_every_field(client, create_book):
    created = create_book(ORWELL)

    response = client.put(
        f"/books/{created['id']}",
        json={"title": "1984", "author": "G. Orwell"},
    )

    assert response.status_code == 200
    book = response.get_json()
    assert book["id"] == created["id"]
    assert book["title"] == "1984"
    assert book["author"] == "G. Orwell"
    # Omitted optional fields are cleared by a full replacement.
    assert book["year"] is None
    assert book["isbn"] is None
    assert book["created_at"] == created["created_at"]
    assert book["updated_at"] > created["updated_at"]
    assert client.get(f"/books/{created['id']}").get_json() == book


def test_put_unknown_book_returns_404(client):
    response = client.put("/books/999", json={"title": "T", "author": "A"})

    assert response.status_code == 404
    assert response.get_json()["error"] == "not_found"


def test_patch_updates_only_the_given_fields(client, create_book):
    created = create_book(ORWELL)

    response = client.patch(f"/books/{created['id']}", json={"year": 1950})

    assert response.status_code == 200
    book = response.get_json()
    assert book["year"] == 1950
    assert book["title"] == ORWELL["title"]
    assert book["isbn"] == ORWELL["isbn"]


def test_patch_unknown_book_returns_404(client):
    assert client.patch("/books/999", json={"year": 2000}).status_code == 404


def test_delete_removes_the_book(client, create_book):
    created = create_book()

    response = client.delete(f"/books/{created['id']}")

    assert response.status_code == 204
    assert response.get_data() == b""
    assert client.get(f"/books/{created['id']}").status_code == 404
    assert client.get("/books").get_json() == []


def test_delete_is_not_silently_idempotent(client, create_book):
    created = create_book()
    client.delete(f"/books/{created['id']}")

    response = client.delete(f"/books/{created['id']}")

    assert response.status_code == 404
    assert response.get_json()["error"] == "not_found"


def test_ids_are_not_reused_after_deletion(client, create_book):
    first = create_book(ORWELL)
    client.delete(f"/books/{first['id']}")

    second = create_book(HUXLEY)

    assert second["id"] != first["id"]
