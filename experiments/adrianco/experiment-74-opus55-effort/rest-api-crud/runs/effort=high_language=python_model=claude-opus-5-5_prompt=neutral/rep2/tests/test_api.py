def test_health(client):
    status, body, resp = client.request("GET", "/health")
    assert status == 200
    assert body == {"status": "ok", "database": "ok"}
    assert resp.getheader("Content-Type") == "application/json"


def test_create_book(client, book):
    status, body, resp = client.request("POST", "/books", book)
    assert status == 201
    assert isinstance(body["id"], int)
    assert body["title"] == "Dune"
    assert body["isbn"] == "9780441013593"
    assert resp.getheader("Location") == f"/books/{body['id']}"


def test_create_requires_title_and_author(client):
    status, body, _ = client.request("POST", "/books", {"year": 2000})
    assert status == 400
    assert body["error"] == "Validation failed"
    assert set(body["details"]) == {"title", "author"}


def test_create_rejects_malformed_json(client):
    status, body, _ = client.request(
        "POST", "/books", raw=b"{not json", headers={"Content-Type": "application/json"}
    )
    assert status == 400
    assert "JSON" in body["error"]


def test_create_rejects_empty_body(client):
    status, _, _ = client.request("POST", "/books")
    assert status == 400


def test_create_rejects_oversized_body(client):
    status, _, _ = client.request("POST", "/books", raw=b"x" * (65 * 1024))
    assert status == 413


def test_duplicate_isbn_conflict(client, book):
    assert client.request("POST", "/books", book)[0] == 201
    status, body, _ = client.request("POST", "/books", {**book, "title": "Other"})
    assert status == 409


def test_list_books_and_author_filter(client, book):
    client.request("POST", "/books", book)
    client.request("POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    client.request("POST", "/books", {"title": "Persuasion", "author": "Jane Austen"})

    status, body, _ = client.request("GET", "/books")
    assert status == 200
    assert [b["title"] for b in body] == ["Dune", "Emma", "Persuasion"]

    status, body, _ = client.request("GET", "/books?author=jane%20austen")
    assert status == 200
    assert [b["title"] for b in body] == ["Emma", "Persuasion"]

    status, body, _ = client.request("GET", "/books?author=Nobody")
    assert status == 200
    assert body == []


def test_get_book(client, book):
    created = client.request("POST", "/books", book)[1]
    status, body, _ = client.request("GET", f"/books/{created['id']}")
    assert status == 200
    assert body == created


def test_get_missing_book_returns_404(client):
    status, body, _ = client.request("GET", "/books/999")
    assert status == 404
    assert body == {"error": "Book not found"}


def test_non_numeric_id_returns_404(client):
    assert client.request("GET", "/books/abc")[0] == 404


def test_update_book(client, book):
    created = client.request("POST", "/books", book)[1]
    changes = {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}
    status, body, _ = client.request("PUT", f"/books/{created['id']}", changes)
    assert status == 200
    assert body == {"id": created["id"], **changes, "isbn": None}
    assert client.request("GET", f"/books/{created['id']}")[1] == body


def test_update_validates_input(client, book):
    created = client.request("POST", "/books", book)[1]
    status, body, _ = client.request("PUT", f"/books/{created['id']}", {"title": ""})
    assert status == 400
    assert set(body["details"]) == {"title", "author"}
    # Unchanged after the failed update.
    assert client.request("GET", f"/books/{created['id']}")[1] == created


def test_update_rejects_mismatched_body_id(client, book):
    created = client.request("POST", "/books", book)[1]
    status, _, _ = client.request(
        "PUT", f"/books/{created['id']}", {**book, "id": created["id"] + 1}
    )
    assert status == 400


def test_update_missing_book_returns_404(client, book):
    assert client.request("PUT", "/books/999", book)[0] == 404


def test_update_isbn_conflict(client, book):
    client.request("POST", "/books", book)
    other = client.request("POST", "/books", {"title": "Emma", "author": "Jane Austen"})[1]
    status, _, _ = client.request(
        "PUT", f"/books/{other['id']}", {"title": "Emma", "author": "Jane Austen", "isbn": book["isbn"]}
    )
    assert status == 409


def test_delete_book(client, book):
    created = client.request("POST", "/books", book)[1]
    status, body, _ = client.request("DELETE", f"/books/{created['id']}")
    assert status == 204
    assert body is None
    assert client.request("GET", f"/books/{created['id']}")[0] == 404
    assert client.request("DELETE", f"/books/{created['id']}")[0] == 404


def test_unknown_route_and_method(client):
    assert client.request("GET", "/nope")[0] == 404
    status, _, resp = client.request("PATCH", "/books/1", {"title": "x"})
    assert status == 405
    assert resp.getheader("Allow") == "DELETE, GET, PUT"


def test_trailing_slash_tolerated(client):
    assert client.request("GET", "/books/")[0] == 200
