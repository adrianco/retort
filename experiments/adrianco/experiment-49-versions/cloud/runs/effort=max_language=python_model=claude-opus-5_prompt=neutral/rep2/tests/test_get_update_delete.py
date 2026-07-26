"""Tests for GET/PUT/PATCH/DELETE on a single book."""

from __future__ import annotations


def test_get_returns_the_book(client, create_book):
    book = create_book()

    response = client.get("/books/{}".format(book["id"]))

    assert response.status_code == 200
    assert response.get_json() == book


def test_get_returns_404_for_an_unknown_id(client):
    response = client.get("/books/4242")

    assert response.status_code == 404
    body = response.get_json()
    assert body["error"] == "not_found"
    assert "4242" in body["message"]


def test_get_returns_404_for_a_non_numeric_id(client):
    response = client.get("/books/not-a-number")

    assert response.status_code == 404
    assert response.get_json()["error"] == "not_found"


def test_put_replaces_every_field(client, create_book):
    book = create_book()

    response = client.put(
        "/books/{}".format(book["id"]),
        json={
            "title": "Dune Messiah",
            "author": "F. Herbert",
            "year": 1969,
            "isbn": "9780593098233",
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["id"] == book["id"]
    assert body["title"] == "Dune Messiah"
    assert body["author"] == "F. Herbert"
    assert body["year"] == 1969
    assert body["isbn"] == "9780593098233"
    assert body["created_at"] == book["created_at"]
    assert body["updated_at"] >= book["updated_at"]


def test_put_is_persisted(client, create_book):
    book = create_book()

    client.put("/books/{}".format(book["id"]), json={"title": "New", "author": "Someone"})

    assert client.get("/books/{}".format(book["id"])).get_json()["title"] == "New"


def test_put_clears_omitted_optional_fields(client, create_book):
    book = create_book(year=1965, isbn="9780441013593")

    response = client.put("/books/{}".format(book["id"]), json={"title": "Dune", "author": "Frank Herbert"})

    body = response.get_json()
    assert body["year"] is None
    assert body["isbn"] is None


def test_put_accepts_a_book_read_back_from_the_api(client, create_book):
    book = create_book()
    book["title"] = "Dune (annotated)"

    response = client.put("/books/{}".format(book["id"]), json=book)

    assert response.status_code == 200
    assert response.get_json()["title"] == "Dune (annotated)"


def test_put_requires_title_and_author(client, create_book):
    book = create_book()

    response = client.put("/books/{}".format(book["id"]), json={"year": 1970})

    assert response.status_code == 400
    assert set(response.get_json()["details"]) == {"title", "author"}


def test_put_returns_404_for_an_unknown_id(client):
    response = client.put("/books/4242", json={"title": "Ghost", "author": "Nobody"})

    assert response.status_code == 404
    assert response.get_json()["error"] == "not_found"


def test_put_does_not_create_the_missing_book(client):
    client.put("/books/4242", json={"title": "Ghost", "author": "Nobody"})

    assert client.get("/books").get_json() == []


def test_put_rejects_an_isbn_owned_by_another_book(client, create_book):
    create_book(title="Dune", isbn="9780441013593")
    other = create_book(title="Neuromancer", author="William Gibson", isbn=None)

    response = client.put(
        "/books/{}".format(other["id"]),
        json={"title": "Neuromancer", "author": "William Gibson", "isbn": "978-0-441-01359-3"},
    )

    assert response.status_code == 409


def test_put_may_keep_its_own_isbn(client, create_book):
    book = create_book(isbn="9780441013593")

    response = client.put(
        "/books/{}".format(book["id"]),
        json={"title": "Dune", "author": "Frank Herbert", "isbn": "9780441013593"},
    )

    assert response.status_code == 200


def test_patch_updates_only_the_supplied_fields(client, create_book):
    book = create_book()

    response = client.patch("/books/{}".format(book["id"]), json={"year": 2005})

    assert response.status_code == 200
    body = response.get_json()
    assert body["year"] == 2005
    assert body["title"] == book["title"]
    assert body["author"] == book["author"]
    assert body["isbn"] == book["isbn"]


def test_patch_can_clear_an_optional_field(client, create_book):
    book = create_book()

    response = client.patch("/books/{}".format(book["id"]), json={"isbn": None})

    assert response.get_json()["isbn"] is None


def test_patch_rejects_an_empty_payload(client, create_book):
    book = create_book()

    response = client.patch("/books/{}".format(book["id"]), json={})

    assert response.status_code == 400
    assert response.get_json()["error"] == "validation_error"


def test_patch_rejects_an_invalid_value(client, create_book):
    book = create_book()

    response = client.patch("/books/{}".format(book["id"]), json={"title": ""})

    assert response.status_code == 400
    assert "title" in response.get_json()["details"]


def test_patch_returns_404_for_an_unknown_id(client):
    response = client.patch("/books/4242", json={"title": "Ghost"})

    assert response.status_code == 404


def test_delete_returns_204_and_no_body(client, create_book):
    book = create_book()

    response = client.delete("/books/{}".format(book["id"]))

    assert response.status_code == 204
    assert response.get_data() == b""
    assert "Content-Type" not in response.headers


def test_a_deleted_book_is_gone(client, create_book):
    book = create_book()
    client.delete("/books/{}".format(book["id"]))

    assert client.get("/books/{}".format(book["id"])).status_code == 404


def test_deleting_twice_returns_404(client, create_book):
    book = create_book()
    client.delete("/books/{}".format(book["id"]))

    response = client.delete("/books/{}".format(book["id"]))

    assert response.status_code == 404
    assert response.get_json()["error"] == "not_found"


def test_deleting_frees_the_isbn(client, create_book):
    book = create_book(isbn="9780441013593")
    client.delete("/books/{}".format(book["id"]))

    assert create_book(isbn="9780441013593")["isbn"] == "9780441013593"
