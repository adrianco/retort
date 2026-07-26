"""Integration tests driving the API through Flask's test client."""

DUNE_ISBN13 = "9780441013593"
DUNE_ISBN10 = "0441013597"
LOTR_ISBN13 = "9780261102217"


def test_health_reports_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}


def test_create_book_returns_201_with_id_and_location(client):
    response = client.post(
        "/books",
        json={"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": DUNE_ISBN13},
    )
    assert response.status_code == 201
    body = response.get_json()
    assert isinstance(body["id"], int)
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"
    assert body["year"] == 1965
    assert body["isbn"] == DUNE_ISBN13
    assert response.headers["Location"].endswith(f"/books/{body['id']}")


def test_create_book_trims_whitespace_and_defaults_optional_fields(client):
    body = client.post(
        "/books", json={"title": "  Emma  ", "author": "  Jane Austen "}
    ).get_json()
    assert body["title"] == "Emma"
    assert body["author"] == "Jane Austen"
    assert body["year"] is None
    assert body["isbn"] is None


def test_created_book_is_persisted_and_retrievable(client, make_book):
    created = make_book()
    response = client.get(f"/books/{created['id']}")
    assert response.status_code == 200
    assert response.get_json() == created


class TestValidation:
    def test_missing_title_and_author_are_reported(self, client):
        response = client.post("/books", json={"year": 1965})
        assert response.status_code == 400
        details = response.get_json()["details"]
        assert details["title"] == "is required"
        assert details["author"] == "is required"

    def test_blank_title_is_rejected(self, client):
        response = client.post("/books", json={"title": "   ", "author": "Someone"})
        assert response.status_code == 400
        assert response.get_json()["details"]["title"] == "must not be empty"

    def test_non_integer_year_is_rejected(self, client):
        response = client.post(
            "/books", json={"title": "Dune", "author": "Herbert", "year": "1965"}
        )
        assert response.status_code == 400
        assert "integer" in response.get_json()["details"]["year"]

    def test_invalid_isbn_checksum_is_rejected(self, client):
        response = client.post(
            "/books",
            json={"title": "Dune", "author": "Herbert", "isbn": "978-0-441-01359-4"},
        )
        assert response.status_code == 400
        assert "ISBN" in response.get_json()["details"]["isbn"]

    def test_hyphenated_isbn_is_normalized(self, client):
        body = client.post(
            "/books",
            json={"title": "Dune", "author": "Herbert", "isbn": "0-441-01359-7"},
        ).get_json()
        assert body["isbn"] == DUNE_ISBN10

    def test_unknown_fields_are_rejected(self, client):
        response = client.post(
            "/books", json={"title": "Dune", "author": "Herbert", "pages": 412}
        )
        assert response.status_code == 400
        assert "pages" in response.get_json()["details"]["body"]

    def test_non_json_body_is_rejected(self, client):
        response = client.post("/books", data="title=Dune", content_type="text/plain")
        assert response.status_code == 400
        assert "application/json" in response.get_json()["details"]["body"]

    def test_malformed_json_is_rejected(self, client):
        response = client.post(
            "/books", data="{not json", content_type="application/json"
        )
        assert response.status_code == 400

    def test_duplicate_isbn_returns_409(self, client, make_book):
        make_book(isbn=DUNE_ISBN13)
        response = client.post(
            "/books", json={"title": "Dune reprint", "author": "Herbert", "isbn": DUNE_ISBN13}
        )
        assert response.status_code == 409
        assert "isbn" in response.get_json()["details"]


class TestList:
    def test_empty_collection(self, client):
        response = client.get("/books")
        assert response.status_code == 200
        assert response.get_json() == {"books": [], "count": 0}

    def test_lists_books_in_insertion_order(self, client, make_book):
        first = make_book(title="Dune")
        second = make_book(title="The Hobbit", author="J. R. R. Tolkien")
        body = client.get("/books").get_json()
        assert body["count"] == 2
        assert [b["id"] for b in body["books"]] == [first["id"], second["id"]]

    def test_author_filter_is_case_insensitive(self, client, make_book):
        make_book(title="Dune", author="Frank Herbert")
        make_book(title="The Hobbit", author="J. R. R. Tolkien")
        body = client.get("/books?author=frank%20herbert").get_json()
        assert body["count"] == 1
        assert body["books"][0]["title"] == "Dune"

    def test_author_filter_with_no_matches_returns_empty_list(self, client, make_book):
        make_book()
        response = client.get("/books?author=Nobody")
        assert response.status_code == 200
        assert response.get_json() == {"books": [], "count": 0}


class TestUpdate:
    def test_put_replaces_all_fields(self, client, make_book):
        created = make_book(isbn=DUNE_ISBN13)
        response = client.put(
            f"/books/{created['id']}",
            json={
                "title": "The Lord of the Rings",
                "author": "J. R. R. Tolkien",
                "year": 1954,
                "isbn": LOTR_ISBN13,
            },
        )
        assert response.status_code == 200
        assert response.get_json() == {
            "id": created["id"],
            "title": "The Lord of the Rings",
            "author": "J. R. R. Tolkien",
            "year": 1954,
            "isbn": LOTR_ISBN13,
        }
        assert client.get(f"/books/{created['id']}").get_json()["year"] == 1954

    def test_put_clears_omitted_optional_fields(self, client, make_book):
        created = make_book(year=1965, isbn=DUNE_ISBN13)
        body = client.put(
            f"/books/{created['id']}", json={"title": "Dune", "author": "Frank Herbert"}
        ).get_json()
        assert body["year"] is None
        assert body["isbn"] is None

    def test_put_validates_before_touching_the_database(self, client, make_book):
        created = make_book()
        response = client.put(f"/books/{created['id']}", json={"author": "Nobody"})
        assert response.status_code == 400
        assert client.get(f"/books/{created['id']}").get_json() == created

    def test_put_on_missing_book_returns_404(self, client):
        response = client.put("/books/999", json={"title": "X", "author": "Y"})
        assert response.status_code == 404
        assert "not found" in response.get_json()["error"]

    def test_put_with_another_books_isbn_returns_409(self, client, make_book):
        make_book(title="Dune", isbn=DUNE_ISBN13)
        other = make_book(title="The Hobbit", author="Tolkien", isbn=LOTR_ISBN13)
        response = client.put(
            f"/books/{other['id']}",
            json={"title": "The Hobbit", "author": "Tolkien", "isbn": DUNE_ISBN13},
        )
        assert response.status_code == 409

    def test_put_keeping_its_own_isbn_succeeds(self, client, make_book):
        created = make_book(isbn=DUNE_ISBN13)
        response = client.put(
            f"/books/{created['id']}",
            json={"title": "Dune (revised)", "author": "Frank Herbert", "isbn": DUNE_ISBN13},
        )
        assert response.status_code == 200
        assert response.get_json()["title"] == "Dune (revised)"


class TestDelete:
    def test_delete_returns_204_and_removes_the_book(self, client, make_book):
        created = make_book()
        response = client.delete(f"/books/{created['id']}")
        assert response.status_code == 204
        assert response.get_data() == b""
        assert client.get(f"/books/{created['id']}").status_code == 404
        assert client.get("/books").get_json()["count"] == 0

    def test_delete_is_not_idempotent_in_status(self, client, make_book):
        created = make_book()
        client.delete(f"/books/{created['id']}")
        assert client.delete(f"/books/{created['id']}").status_code == 404


class TestErrorShape:
    def test_missing_book_returns_json_404(self, client):
        response = client.get("/books/4242")
        assert response.status_code == 404
        assert response.is_json
        assert response.get_json()["error"] == "Book 4242 not found"

    def test_unknown_route_returns_json_404(self, client):
        response = client.get("/nope")
        assert response.status_code == 404
        assert response.is_json

    def test_wrong_method_returns_json_405(self, client):
        response = client.patch("/books", json={})
        assert response.status_code == 405
        assert response.is_json

    def test_non_integer_id_returns_404(self, client):
        assert client.get("/books/abc").status_code == 404
