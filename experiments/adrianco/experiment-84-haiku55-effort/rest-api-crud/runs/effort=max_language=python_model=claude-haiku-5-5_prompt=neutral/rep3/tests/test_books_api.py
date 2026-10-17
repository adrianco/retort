import pytest

from bookapi import create_app

HOBBIT = {
    "title": "The Hobbit",
    "author": "J.R.R. Tolkien",
    "year": 1937,
    "isbn": "978-0-547-92822-7",
}


def add_book(client, **overrides):
    response = client.post("/books", json={**HOBBIT, **overrides})
    assert response.status_code == 201
    return response.get_json()


def titles(response):
    return [book["title"] for book in response.get_json()]


def test_health_reports_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}


def test_health_reports_unavailable_database(app, client, tmp_path):
    app.config["DATABASE"] = str(tmp_path / "missing-dir" / "books.db")

    response = client.get("/health")

    assert response.status_code == 503
    assert response.get_json() == {"status": "error", "database": "unavailable"}


def test_create_book_returns_201_with_location_and_normalized_isbn(client):
    response = client.post("/books", json=HOBBIT)

    assert response.status_code == 201
    assert response.headers["Location"] == "/books/1"
    assert response.get_json() == {
        "id": 1,
        "title": "The Hobbit",
        "author": "J.R.R. Tolkien",
        "year": 1937,
        "isbn": "9780547928227",
    }


def test_create_book_treats_year_and_isbn_as_optional(client):
    response = client.post("/books", json={"title": "Untitled", "author": "Anon"})

    assert response.status_code == 201
    assert response.get_json()["year"] is None
    assert response.get_json()["isbn"] is None


def test_create_book_requires_title_and_author(client):
    response = client.post("/books", json={"year": 1937})

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Validation failed",
        "details": {"title": "Title is required", "author": "Author is required"},
    }
    assert client.get("/books").get_json() == []


def test_create_book_rejects_invalid_isbn(client):
    response = client.post("/books", json={**HOBBIT, "isbn": "978-0-547-92822-8"})

    assert response.status_code == 400
    assert response.get_json()["details"] == {"isbn": "Must be a valid ISBN-10 or ISBN-13"}


@pytest.mark.parametrize("body", [[1, 2, 3], "just a string"])
def test_create_book_requires_a_json_object(client, body):
    response = client.post("/books", json=body)

    assert response.status_code == 400
    assert response.get_json() == {"error": "Request body must be a JSON object"}


def test_create_book_rejects_malformed_json(client):
    response = client.post("/books", data="{not json", content_type="application/json")

    assert response.status_code == 400
    assert response.get_json() == {"error": "Request body must be a JSON object"}


def test_list_books_is_empty_for_a_new_collection(client):
    response = client.get("/books")

    assert response.status_code == 200
    assert response.get_json() == []


def test_list_books_returns_every_book_in_id_order(client):
    add_book(client, title="Book A")
    add_book(client, title="Book B")

    assert titles(client.get("/books")) == ["Book A", "Book B"]


def test_list_books_filters_by_author(client):
    add_book(client, title="The Hobbit", author="J.R.R. Tolkien")
    add_book(client, title="1984", author="George Orwell", year=1949, isbn=None)
    add_book(client, title="Animal Farm", author="George Orwell", year=1945, isbn=None)

    response = client.get("/books", query_string={"author": "George Orwell"})

    assert response.status_code == 200
    assert titles(response) == ["1984", "Animal Farm"]


def test_author_filter_ignores_case_and_needs_the_full_name(client):
    add_book(client, title="1984", author="George Orwell", year=1949, isbn=None)

    assert titles(client.get("/books?author=george orwell")) == ["1984"]
    assert client.get("/books?author=Orwell").get_json() == []


def test_list_books_rejects_blank_author_filter(client):
    response = client.get("/books", query_string={"author": "   "})

    assert response.status_code == 400
    assert response.get_json()["details"] == {"author": "Must not be blank"}


def test_get_book_returns_the_book(client):
    created = add_book(client)

    response = client.get(f"/books/{created['id']}")

    assert response.status_code == 200
    assert response.get_json() == created


def test_get_missing_book_returns_404(client):
    response = client.get("/books/999")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Book 999 not found"}


def test_non_integer_book_id_returns_json_404(client):
    response = client.get("/books/abc")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Not Found"}


def test_update_replaces_the_book(client):
    created = add_book(client)

    response = client.put(
        f"/books/{created['id']}",
        json={"title": "The Hobbit, 2nd ed.", "author": "J. R. R. Tolkien"},
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "id": created["id"],
        "title": "The Hobbit, 2nd ed.",
        "author": "J. R. R. Tolkien",
        "year": None,
        "isbn": None,
    }
    assert client.get(f"/books/{created['id']}").get_json() == response.get_json()


def test_update_with_invalid_body_leaves_the_book_unchanged(client):
    created = add_book(client)

    response = client.put(f"/books/{created['id']}", json={"title": "", "author": "Anon"})

    assert response.status_code == 400
    assert client.get(f"/books/{created['id']}").get_json() == created


def test_update_missing_book_returns_404(client):
    response = client.put("/books/42", json=HOBBIT)

    assert response.status_code == 404
    assert response.get_json() == {"error": "Book 42 not found"}


def test_delete_removes_the_book(client):
    created = add_book(client)

    response = client.delete(f"/books/{created['id']}")

    assert response.status_code == 204
    assert response.data == b""
    assert client.get(f"/books/{created['id']}").status_code == 404


def test_delete_missing_book_returns_404(client):
    response = client.delete("/books/7")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Book 7 not found"}


def test_ids_are_not_reused_after_delete(client):
    first = add_book(client)
    client.delete(f"/books/{first['id']}")

    second = add_book(client)

    assert second["id"] == first["id"] + 1


def test_unknown_route_returns_json_404(client):
    response = client.get("/authors")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Not Found"}


def test_unsupported_method_returns_json_405_with_allow_header(client):
    response = client.patch("/books/1")

    assert response.status_code == 405
    assert response.get_json() == {"error": "Method Not Allowed"}
    allowed = {method.strip() for method in response.headers["Allow"].split(",")}
    assert {"GET", "PUT", "DELETE"} <= allowed


def test_database_path_comes_from_environment(tmp_path, monkeypatch):
    database = tmp_path / "from-env.db"
    monkeypatch.setenv("BOOKAPI_DATABASE", str(database))

    app = create_app()

    assert app.config["DATABASE"] == str(database)
    assert database.exists()


def test_books_persist_across_app_instances(tmp_path):
    config = {"TESTING": True, "DATABASE": str(tmp_path / "books.db")}
    first = create_app(config).test_client()
    add_book(first, title="Persisted")

    second = create_app(config).test_client()

    assert titles(second.get("/books")) == ["Persisted"]
