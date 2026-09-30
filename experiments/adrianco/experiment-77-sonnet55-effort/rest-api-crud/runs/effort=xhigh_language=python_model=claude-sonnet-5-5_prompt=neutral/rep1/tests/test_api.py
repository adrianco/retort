"""Integration tests for the HTTP API, exercised through the WSGI callable."""

import pytest


class TestHealth:
    def test_health_ok(self, client):
        reply = client.get("/health")
        assert reply.status == 200
        assert reply.json == {"status": "ok"}
        assert reply.headers["Content-Type"] == "application/json"

    def test_health_reports_unavailable_when_db_is_closed(self, app, client):
        app.repository.close()
        reply = client.get("/health")
        assert reply.status == 503
        assert reply.json == {"status": "unavailable"}

    def test_head_health_has_no_body(self, client):
        reply = client.request("HEAD", "/health")
        assert reply.status == 200
        assert reply.raw == b""
        assert int(reply.headers["Content-Length"]) > 0


class TestCreateBook:
    def test_create_returns_201_with_location_and_full_book(self, client):
        payload = {
            "title": "Dune",
            "author": "Frank Herbert",
            "year": 1965,
            "isbn": "9780441172719",
        }
        reply = client.post("/books", payload)
        assert reply.status == 201
        assert reply.json == {"id": 1, **payload}
        assert reply.headers["Location"] == "/books/1"

    def test_year_and_isbn_are_optional(self, client):
        reply = client.post("/books", {"title": "Dune", "author": "Frank Herbert"})
        assert reply.status == 201
        assert reply.json["year"] is None
        assert reply.json["isbn"] is None

    def test_ids_are_assigned_sequentially(self, make_book):
        assert [make_book()["id"] for _ in range(3)] == [1, 2, 3]

    def test_text_is_trimmed(self, client):
        reply = client.post("/books", {"title": "  Dune ", "author": " Frank Herbert  "})
        assert reply.json["title"] == "Dune"
        assert reply.json["author"] == "Frank Herbert"

    def test_unicode_round_trips(self, client):
        reply = client.post("/books", {"title": "Les Misérables", "author": "Victor Hugo 雨果"})
        assert client.get("/books/1").json == reply.json
        assert reply.json["title"] == "Les Misérables"

    @pytest.mark.parametrize(
        "payload, bad_fields",
        [
            ({}, {"title", "author"}),
            ({"author": "A"}, {"title"}),
            ({"title": "T"}, {"author"}),
            ({"title": "", "author": "A"}, {"title"}),
            ({"title": "T", "author": "   "}, {"author"}),
            ({"title": None, "author": "A"}, {"title"}),
            ({"title": 123, "author": "A"}, {"title"}),
            ({"title": "T", "author": "A", "year": "1949"}, {"year"}),
            ({"title": "T", "author": "A", "year": 19.49}, {"year"}),
            ({"title": "T", "author": "A", "year": True}, {"year"}),
            ({"title": "T", "author": "A", "year": 10000}, {"year"}),
            ({"title": "T", "author": "A", "isbn": 9780441172719}, {"isbn"}),
            ({"title": "x" * 256, "author": "A"}, {"title"}),
            ({"title": "", "author": "", "year": "x"}, {"title", "author", "year"}),
        ],
    )
    def test_invalid_payload_returns_400_naming_each_bad_field(
        self, client, payload, bad_fields
    ):
        reply = client.post("/books", payload)
        assert reply.status == 400
        assert reply.json["error"] == "Validation failed"
        assert set(reply.json["details"]) == bad_fields
        assert client.get("/books").json == []  # nothing was stored

    @pytest.mark.parametrize(
        "raw",
        [b"", b"   ", b"{not json", b"\xff\xfe", b"[1, 2]", b'"a string"', b"null", b"42"],
    )
    def test_malformed_or_non_object_body_returns_400(self, client, raw):
        reply = client.post("/books", raw=raw)
        assert reply.status == 400
        assert "error" in reply.json

    def test_oversized_body_returns_413(self, client):
        reply = client.post(
            "/books", raw=b"{}", environ_extra={"CONTENT_LENGTH": str(10_000_000)}
        )
        assert reply.status == 413

    @pytest.mark.parametrize("length", ["abc", "-5"])
    def test_bad_content_length_returns_400(self, client, length):
        reply = client.post("/books", raw=b"{}", environ_extra={"CONTENT_LENGTH": length})
        assert reply.status == 400

    def test_unknown_fields_are_ignored(self, client):
        reply = client.post(
            "/books", {"title": "T", "author": "A", "id": 99, "rating": 5}
        )
        assert reply.status == 201
        assert reply.json == {"id": 1, "title": "T", "author": "A", "year": None, "isbn": None}


class TestListBooks:
    def test_empty_collection_returns_empty_list(self, client):
        reply = client.get("/books")
        assert reply.status == 200
        assert reply.json == []

    def test_lists_all_books_in_id_order(self, client, make_book):
        make_book(title="B")
        make_book(title="A")
        assert [b["title"] for b in client.get("/books").json] == ["B", "A"]

    def test_author_filter(self, client, make_book):
        make_book(title="1984", author="George Orwell")
        make_book(title="Animal Farm", author="George Orwell")
        make_book(title="Dune", author="Frank Herbert")

        reply = client.get("/books?author=George%20Orwell")
        assert reply.status == 200
        assert [b["title"] for b in reply.json] == ["1984", "Animal Farm"]

        assert [b["title"] for b in client.get("/books?author=Frank+Herbert").json] == ["Dune"]

    def test_author_filter_is_case_insensitive_and_exact(self, client, make_book):
        make_book(author="George Orwell")
        assert len(client.get("/books?author=george%20orwell").json) == 1
        assert client.get("/books?author=Orwell").json == []

    def test_author_filter_handles_non_ascii_case(self, client, make_book):
        make_book(author="Émile Zola")
        assert len(client.get("/books?author=%C3%A9mile%20zola").json) == 1

    def test_author_filter_with_no_matches_returns_empty_list(self, client, make_book):
        make_book()
        reply = client.get("/books?author=Nobody")
        assert reply.status == 200
        assert reply.json == []

    def test_blank_author_filter_is_ignored(self, client, make_book):
        make_book()
        assert len(client.get("/books?author=").json) == 1

    def test_author_filter_is_not_vulnerable_to_sql_injection(self, client, make_book):
        make_book()
        assert client.get("/books?author=x'%20OR%20'1'='1").json == []
        assert len(client.get("/books").json) == 1

    def test_trailing_slash_is_accepted(self, client, make_book):
        make_book()
        assert len(client.get("/books/").json) == 1


class TestGetBook:
    def test_get_existing_book(self, client, make_book):
        book = make_book()
        reply = client.get(f"/books/{book['id']}")
        assert reply.status == 200
        assert reply.json == book

    @pytest.mark.parametrize(
        "book_id",
        ["999", "0", "abc", "-1", "1.5", "9999999999999999999", "99999999999999999999999"],
    )
    def test_missing_or_malformed_id_returns_404(self, client, book_id):
        reply = client.get(f"/books/{book_id}")
        assert reply.status == 404
        assert reply.json == {"error": "Book not found"}


class TestUpdateBook:
    def test_full_update(self, client, make_book):
        book = make_book()
        replacement = {
            "title": "Animal Farm",
            "author": "G. Orwell",
            "year": 1945,
            "isbn": "978-0451526342",
        }
        reply = client.put(f"/books/{book['id']}", replacement)
        assert reply.status == 200
        assert reply.json == {"id": book["id"], **replacement}
        assert client.get(f"/books/{book['id']}").json == reply.json

    def test_partial_update_keeps_other_fields(self, client, make_book):
        book = make_book()
        reply = client.put(f"/books/{book['id']}", {"year": 1950})
        assert reply.status == 200
        assert reply.json == {**book, "year": 1950}

    def test_null_clears_optional_fields(self, client, make_book):
        book = make_book()
        reply = client.put(f"/books/{book['id']}", {"year": None, "isbn": None})
        assert reply.status == 200
        assert reply.json["year"] is None and reply.json["isbn"] is None
        assert reply.json["title"] == book["title"]

    def test_update_does_not_touch_other_books(self, client, make_book):
        first, second = make_book(title="One"), make_book(title="Two")
        client.put(f"/books/{first['id']}", {"title": "Changed"})
        assert client.get(f"/books/{second['id']}").json == second

    def test_id_in_body_cannot_change_the_id(self, client, make_book):
        book = make_book()
        reply = client.put(f"/books/{book['id']}", {"id": 42, "title": "New"})
        assert reply.json["id"] == book["id"]

    @pytest.mark.parametrize(
        "payload, bad_field",
        [
            ({"title": ""}, "title"),
            ({"author": "  "}, "author"),
            ({"title": None}, "title"),
            ({"year": "1949"}, "year"),
            ({"isbn": 5}, "isbn"),
            ({}, "body"),
            ({"unknown": 1}, "body"),
        ],
    )
    def test_invalid_update_returns_400_and_changes_nothing(
        self, client, make_book, payload, bad_field
    ):
        book = make_book()
        reply = client.put(f"/books/{book['id']}", payload)
        assert reply.status == 400
        assert bad_field in reply.json["details"]
        assert client.get(f"/books/{book['id']}").json == book

    def test_non_json_body_returns_400(self, client, make_book):
        book = make_book()
        assert client.put(f"/books/{book['id']}", raw=b"nope").status == 400

    def test_update_missing_book_returns_404(self, client):
        reply = client.put("/books/999", {"title": "T"})
        assert reply.status == 404
        assert reply.json == {"error": "Book not found"}

    def test_update_missing_book_is_404_even_with_invalid_body(self, client):
        assert client.put("/books/999", {"title": ""}).status == 404

    def test_update_of_book_deleted_mid_request_returns_404(
        self, app, client, make_book, monkeypatch
    ):
        book = make_book()
        real_update = app.repository.update

        def delete_then_update(book_id, fields):
            app.repository.delete(book_id)
            return real_update(book_id, fields)

        monkeypatch.setattr(app.repository, "update", delete_then_update)
        assert client.put(f"/books/{book['id']}", {"title": "New"}).status == 404


class TestDeleteBook:
    def test_delete_returns_204_and_removes_book(self, client, make_book):
        book = make_book()
        reply = client.delete(f"/books/{book['id']}")
        assert reply.status == 204
        assert reply.raw == b""
        assert client.get(f"/books/{book['id']}").status == 404
        assert client.get("/books").json == []

    def test_delete_only_removes_the_target(self, client, make_book):
        keep, drop = make_book(title="Keep"), make_book(title="Drop")
        client.delete(f"/books/{drop['id']}")
        assert client.get("/books").json == [keep]

    def test_deleted_ids_are_not_reused(self, client, make_book):
        first = make_book()
        client.delete(f"/books/{first['id']}")
        assert make_book()["id"] == first["id"] + 1

    def test_delete_missing_book_returns_404(self, client):
        reply = client.delete("/books/999")
        assert reply.status == 404
        assert reply.json == {"error": "Book not found"}

    def test_delete_twice_returns_404_the_second_time(self, client, make_book):
        book = make_book()
        assert client.delete(f"/books/{book['id']}").status == 204
        assert client.delete(f"/books/{book['id']}").status == 404


class TestRoutingAndErrors:
    def test_unknown_path_returns_json_404(self, client):
        reply = client.get("/nope")
        assert reply.status == 404
        assert reply.json == {"error": "Not found"}

    def test_nested_path_returns_404(self, client):
        assert client.get("/books/1/extra").status == 404

    @pytest.mark.parametrize(
        "method, path, allow",
        [
            ("DELETE", "/books", "GET, HEAD, POST"),
            ("PATCH", "/books/1", "DELETE, GET, HEAD, PUT"),
            ("POST", "/health", "GET, HEAD"),
            ("POST", "/books/1", "DELETE, GET, HEAD, PUT"),
        ],
    )
    def test_wrong_method_returns_405_with_allow_header(self, client, method, path, allow):
        reply = client.request(method, path)
        assert reply.status == 405
        assert reply.headers["Allow"] == allow

    def test_unexpected_error_returns_json_500_without_leaking_details(
        self, app, client, monkeypatch
    ):
        def boom(**_):
            raise RuntimeError("secret internal detail")

        monkeypatch.setattr(app.repository, "list_books", boom)
        reply = client.get("/books")
        assert reply.status == 500
        assert reply.json == {"error": "Internal server error"}
        assert b"secret" not in reply.raw
