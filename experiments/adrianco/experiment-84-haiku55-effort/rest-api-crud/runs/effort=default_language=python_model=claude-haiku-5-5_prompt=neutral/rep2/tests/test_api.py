def test_health_reports_ok(api):
    status, _, body = api("GET", "/health")
    assert status == 200
    assert body == {"status": "ok"}


def test_create_book_returns_201_with_location_and_stored_fields(api, sample_book):
    status, headers, body = api("POST", "/books", sample_book)

    assert status == 201
    assert headers["Location"] == f"/books/{body['id']}"
    assert body["id"] >= 1
    assert body["title"] == "The Pragmatic Programmer"
    assert body["author"] == "Andrew Hunt"
    assert body["year"] == 1999
    assert body["isbn"] == "020161622X"  # normalised: hyphens removed, upper-case


def test_create_book_allows_missing_optional_fields(api):
    status, _, body = api("POST", "/books", {"title": "Dune", "author": "Frank Herbert"})

    assert status == 201
    assert body["year"] is None
    assert body["isbn"] is None


def test_create_book_requires_title_and_author(api):
    status, _, body = api("POST", "/books", {"year": 2000})

    assert status == 400
    assert body["error"] == "validation failed"
    assert body["details"] == {"title": "is required", "author": "is required"}


def test_create_book_rejects_blank_title(api):
    status, _, body = api("POST", "/books", {"title": "   ", "author": "Someone"})

    assert status == 400
    assert "title" in body["details"]


def test_create_book_rejects_invalid_isbn_checksum(api, sample_book):
    status, _, body = api("POST", "/books", {**sample_book, "isbn": "0201616223"})

    assert status == 400
    assert "isbn" in body["details"]


def test_create_book_rejects_non_integer_year(api, sample_book):
    status, _, body = api("POST", "/books", {**sample_book, "year": "1999"})

    assert status == 400
    assert body["details"] == {"year": "must be an integer"}


def test_create_book_rejects_malformed_json(api):
    status, _, body = api("POST", "/books", raw="{not json")

    assert status == 400
    assert body["error"] == "request body must be valid JSON"


def test_create_book_rejects_non_object_body(api):
    status, _, body = api("POST", "/books", ["not", "an", "object"])

    assert status == 400
    assert body["details"] == {"body": "must be a JSON object"}


def test_duplicate_isbn_returns_409(api, sample_book):
    api("POST", "/books", sample_book)

    status, _, body = api("POST", "/books", {**sample_book, "title": "Another Title"})

    assert status == 409
    assert "ISBN" in body["error"]


def test_list_books_returns_all_books_in_insertion_order(api):
    api("POST", "/books", {"title": "A", "author": "X"})
    api("POST", "/books", {"title": "B", "author": "Y"})

    status, _, body = api("GET", "/books")

    assert status == 200
    assert [book["title"] for book in body] == ["A", "B"]


def test_list_books_filters_by_author_ignoring_case(api):
    api("POST", "/books", {"title": "Book One", "author": "Ursula K. Le Guin"})
    api("POST", "/books", {"title": "Book Two", "author": "Frank Herbert"})
    api("POST", "/books", {"title": "Book Three", "author": "ursula k. le guin"})

    status, _, body = api("GET", "/books?author=URSULA%20K.%20LE%20GUIN")

    assert status == 200
    assert [book["title"] for book in body] == ["Book One", "Book Three"]


def test_list_books_with_unknown_author_returns_empty_list(api, sample_book):
    api("POST", "/books", sample_book)

    status, _, body = api("GET", "/books?author=Nobody")

    assert status == 200
    assert body == []


def test_list_books_rejects_blank_author_filter(api):
    status, _, body = api("GET", "/books?author=%20%20")

    assert status == 400
    assert "author" in body["error"]


def test_get_book_by_id(api, sample_book):
    _, _, created = api("POST", "/books", sample_book)

    status, _, body = api("GET", f"/books/{created['id']}")

    assert status == 200
    assert body == created


def test_get_unknown_book_returns_404(api):
    status, _, body = api("GET", "/books/9999")

    assert status == 404
    assert body["error"] == "book not found"


def test_non_numeric_book_id_is_not_found(api):
    status, _, _ = api("GET", "/books/abc")

    assert status == 404


def test_update_book_replaces_all_fields(api, sample_book):
    _, _, created = api("POST", "/books", sample_book)

    status, _, body = api(
        "PUT",
        f"/books/{created['id']}",
        {"title": "Refactoring", "author": "Martin Fowler", "year": 2018},
    )

    assert status == 200
    assert body == {
        "id": created["id"],
        "title": "Refactoring",
        "author": "Martin Fowler",
        "year": 2018,
        "isbn": None,
    }
    assert api("GET", f"/books/{created['id']}")[2] == body


def test_update_unknown_book_returns_404(api):
    status, _, _ = api("PUT", "/books/9999", {"title": "T", "author": "A"})

    assert status == 404


def test_update_validates_input(api, sample_book):
    _, _, created = api("POST", "/books", sample_book)

    status, _, body = api("PUT", f"/books/{created['id']}", {"title": "T"})

    assert status == 400
    assert body["details"] == {"author": "is required"}


def test_delete_book_then_it_is_gone(api, sample_book):
    _, _, created = api("POST", "/books", sample_book)

    status, _, _ = api("DELETE", f"/books/{created['id']}")
    assert status == 204

    assert api("GET", f"/books/{created['id']}")[0] == 404
    assert api("DELETE", f"/books/{created['id']}")[0] == 404


def test_unknown_route_returns_404(api):
    status, _, body = api("GET", "/nope")

    assert status == 404
    assert body["error"] == "not found"


def test_wrong_method_returns_405_with_allow_header(api):
    status, headers, _ = api("PATCH", "/books/1")

    assert status == 405
    assert set(headers["Allow"].split(", ")) == {"GET", "PUT", "DELETE"}


def test_health_rejects_post(api):
    status, headers, _ = api("POST", "/health")

    assert status == 405
    assert headers["Allow"] == "GET"
