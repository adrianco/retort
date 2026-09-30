"""Behaviour of the REST API, exercised through the WSGI interface (no sockets)."""

import io
import json
import logging
import socket
from datetime import date

import pytest

from bookapi import BookAPI, BookRepository
from bookapi.web import MAX_BODY_BYTES

DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}

# Titles of the books created by TestListBooks.library, in creation order.
LIBRARY_TITLES = ["1984", "Animal Farm", "Dune", "Cien años de soledad"]

# Representative invalid books: (payload, field that must be reported). The exhaustive
# matrix lives in test_validation.py; these prove the rules are wired into POST and PUT.
INVALID_BOOKS = [
    pytest.param({"author": "Someone"}, "title", id="title-missing"),
    pytest.param({"title": "Something"}, "author", id="author-missing"),
    pytest.param({"title": "   ", "author": "Someone"}, "title", id="title-blank"),
    pytest.param({"title": "Something", "author": None}, "author", id="author-null"),
    pytest.param({"title": 42, "author": "Someone"}, "title", id="title-not-a-string"),
    pytest.param({**DUNE, "year": "1965"}, "year", id="year-not-an-integer"),
    pytest.param({**DUNE, "year": date.today().year + 2}, "year", id="year-in-the-far-future"),
    pytest.param({**DUNE, "isbn": 9780441013593}, "isbn", id="isbn-not-a-string"),
    pytest.param({"title": "\ud800", "author": "Someone"}, "title", id="unencodable-text"),
]


class TestCreateBook:
    def test_returns_201_with_the_stored_book(self, client):
        response = client.post("/books", json=DUNE)

        assert response.status_code == 201
        assert response.headers["content-type"] == "application/json"
        book = response.json()
        assert isinstance(book["id"], int)
        assert book == {"id": book["id"], **DUNE}
        assert response.headers["location"] == f"/books/{book['id']}"
        assert int(response.headers["content-length"]) == len(response.body)

    def test_year_and_isbn_are_optional(self, client):
        response = client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})

        assert response.status_code == 201
        assert response.json() == {
            "id": 1,
            "title": "Dune",
            "author": "Frank Herbert",
            "year": None,
            "isbn": None,
        }

    def test_the_book_can_be_read_back(self, client, make_book):
        created = make_book(**DUNE)
        assert client.get(f"/books/{created['id']}").json() == created

    def test_every_book_gets_its_own_id(self, make_book):
        assert len({make_book()["id"] for _ in range(3)}) == 3

    def test_text_is_trimmed_and_a_blank_isbn_is_dropped(self, client):
        payload = {"title": "  Dune ", "author": " Frank Herbert\n", "isbn": "   "}
        book = client.post("/books", json=payload).json()

        assert (book["title"], book["author"], book["isbn"]) == ("Dune", "Frank Herbert", None)

    def test_unknown_fields_and_a_client_chosen_id_are_ignored(self, client):
        book = client.post("/books", json={**DUNE, "id": 999, "rating": 5}).json()

        assert book["id"] != 999
        assert "rating" not in book

    def test_unicode_survives_the_round_trip(self, client):
        payload = {"title": "Cien años de soledad 📚", "author": "Gabriel García Márquez"}
        response = client.post("/books", json=payload)

        assert response.json()["title"] == payload["title"]
        assert "García".encode() in response.body  # sent as UTF-8, not \u escapes
        assert client.get("/books").json()[0]["author"] == payload["author"]

    @pytest.mark.parametrize(
        "content_type", [None, "text/plain", "application/json; charset=utf-8"]
    )
    def test_the_content_type_header_is_not_required(self, client, content_type):
        response = client.post("/books", data=json.dumps(DUNE), content_type=content_type)
        assert response.status_code == 201

    def test_a_utf8_byte_order_mark_is_tolerated(self, client):
        response = client.post("/books", data=b"\xef\xbb\xbf" + json.dumps(DUNE).encode())
        assert response.status_code == 201

    @pytest.mark.parametrize("payload, field", INVALID_BOOKS)
    def test_an_invalid_book_is_rejected_with_400_and_not_stored(self, client, payload, field):
        response = client.post("/books", json=payload)

        assert response.status_code == 400
        assert response.headers["content-type"] == "application/json"
        body = response.json()
        assert body["error"] == "Validation failed"
        assert field in body["details"]
        assert client.get("/books").json() == []

    def test_title_and_author_are_both_required(self, client):
        response = client.post("/books", json={"year": 1965})

        assert response.status_code == 400
        assert response.json()["details"] == {
            "title": "title is required",
            "author": "author is required",
        }

    def test_every_invalid_field_is_reported_at_once(self, client):
        response = client.post("/books", json={"title": "", "author": 7, "year": "x", "isbn": 1})
        assert set(response.json()["details"]) == {"title", "author", "year", "isbn"}

    @pytest.mark.parametrize(
        "body, message",
        [
            (b"", "Request body is required"),
            (b"  \n", "Request body is required"),
            (b"not json", "Request body must be valid JSON"),
            (b'{"title": "x",}', "Request body must be valid JSON"),
            (b"\xff\xfe\xfd", "Request body must be valid JSON"),  # not UTF-8
            (b"[" * 200_000, "Request body must be valid JSON"),  # nested far too deeply
            (b"[]", "Request body must be a JSON object"),
            (b'"text"', "Request body must be a JSON object"),
            (b"42", "Request body must be a JSON object"),
            (b"null", "Request body must be a JSON object"),
        ],
    )
    def test_a_body_that_is_not_a_json_object_is_rejected_with_400(self, client, body, message):
        response = client.post("/books", data=body)

        assert response.status_code == 400
        assert response.json() == {"error": message}

    def test_an_absurdly_long_number_is_a_400_not_a_crash(self, client):
        body = b'{"title": "x", "author": "y", "year": ' + b"9" * 5000 + b"}"
        assert client.post("/books", data=body).status_code == 400

    @pytest.mark.parametrize("length", ["abc", "-5", "1_0", "1.5", "١٢"])
    def test_a_malformed_content_length_is_rejected_with_400(self, wsgi_app, make_client, length):
        client = make_client(wsgi_app, validate=False)
        response = client.post("/books", data=json.dumps(DUNE), environ={"CONTENT_LENGTH": length})

        assert response.status_code == 400
        assert response.json() == {"error": "Invalid Content-Length header"}

    # 5000 digits would make int() raise on Python 3.11+ (its digit limit) if it were called.
    @pytest.mark.parametrize("length", [str(MAX_BODY_BYTES + 1), "9" * 30, "9" * 5000])
    def test_an_oversized_body_is_rejected_with_413_without_being_read(
        self, wsgi_app, make_client, length
    ):
        class MustNotBeRead:
            def read(self, size):
                raise AssertionError("an oversized body must not be read")

        client = make_client(wsgi_app, validate=False)
        response = client.post(
            "/books", environ={"CONTENT_LENGTH": length, "wsgi.input": MustNotBeRead()}
        )

        assert response.status_code == 413
        assert "error" in response.json()

    def test_a_chunked_body_is_rejected_with_411_and_a_clear_message(self, client):
        response = client.post(
            "/books", data=json.dumps(DUNE), environ={"HTTP_TRANSFER_ENCODING": "chunked"}
        )

        assert response.status_code == 411
        assert "Content-Length" in response.json()["error"]

    def test_a_body_that_stalls_mid_transfer_is_a_408(self, client):
        class Stalled(io.BytesIO):  # a full file-like object, as the WSGI validator requires
            def read(self, size=-1):
                raise socket.timeout("timed out")

        response = client.post("/books", environ={"CONTENT_LENGTH": "10", "wsgi.input": Stalled()})
        assert response.status_code == 408


class TestListBooks:
    @pytest.fixture
    def library(self, make_book):
        return {
            "1984": make_book(title="1984", author="George Orwell"),
            "farm": make_book(title="Animal Farm", author="George Orwell"),
            "dune": make_book(title="Dune", author="Frank Herbert"),
            "soledad": make_book(title="Cien años de soledad", author="Gabriel García Márquez"),
        }

    def titles(self, response):
        assert response.status_code == 200
        return [book["title"] for book in response.json()]

    def test_an_empty_collection_is_an_empty_array(self, client):
        response = client.get("/books")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert response.json() == []

    def test_lists_every_book_in_creation_order(self, client, library):
        response = client.get("/books")

        assert response.json() == list(library.values())

    @pytest.mark.parametrize(
        "query, expected",
        [
            ("author=George%20Orwell", ["1984", "Animal Farm"]),
            ("author=George+Orwell", ["1984", "Animal Farm"]),
            ("author=george%20ORWELL", ["1984", "Animal Farm"]),
            ("author=%20George%20Orwell%20", ["1984", "Animal Farm"]),
            ("author=Frank%20Herbert", ["Dune"]),
            ("author=Gabriel%20Garc%C3%ADa%20M%C3%A1rquez", ["Cien años de soledad"]),
            ("author=GABRIEL%20GARC%C3%8DA%20M%C3%81RQUEZ", ["Cien años de soledad"]),
            ("author=Gabriel García Márquez", ["Cien años de soledad"]),  # unencoded UTF-8
            ("author=Nobody", []),
            ("author=Orwell", []),  # exact match, not "contains"
            ("author=George", []),
            ("author=%25", []),  # a literal "%", not a wildcard
            ("author=George%20_rwell", []),  # a literal "_", not a wildcard
            ("author=", LIBRARY_TITLES),  # a blank filter means no filter
            ("author", LIBRARY_TITLES),
            ("unrelated=1", LIBRARY_TITLES),
        ],
    )
    def test_author_filter(self, client, library, query, expected):
        assert self.titles(client.get(f"/books?{query}")) == expected

    def test_a_repeated_author_parameter_is_rejected(self, client, library):
        response = client.get("/books?author=Frank%20Herbert&author=George%20Orwell")

        assert response.status_code == 400
        assert "author" in response.json()["error"]

    def test_the_filter_follows_updates_and_deletes(self, client, library):
        client.put(
            f"/books/{library['dune']['id']}", json={"title": "Dune", "author": "George Orwell"}
        )
        client.delete(f"/books/{library['1984']['id']}")

        assert self.titles(client.get("/books?author=george orwell")) == ["Animal Farm", "Dune"]
        assert self.titles(client.get("/books?author=Frank Herbert")) == []

    @pytest.mark.parametrize("author", ["García", "Ω"])
    def test_servers_that_pass_real_unicode_rather_than_latin1_work_too(
        self, client, make_book, author
    ):
        make_book(title="X", author=author)

        response = client.get("/books", environ={"QUERY_STRING": f"author={author}"})

        assert self.titles(response) == ["X"]

    @pytest.mark.parametrize(
        "query", ["author=%ff%fe", "%", "&&&", "author=%zz", "=", "author=%00"]
    )
    def test_odd_query_strings_never_cause_an_error(self, client, library, query):
        assert client.get(f"/books?{query}").status_code == 200


class TestGetBook:
    def test_returns_the_book(self, client, make_book):
        created = make_book(**DUNE)

        response = client.get(f"/books/{created['id']}")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert response.json() == created

    def test_an_unknown_id_is_404(self, client, make_book):
        make_book()

        response = client.get("/books/12345")

        assert response.status_code == 404
        assert response.headers["content-type"] == "application/json"
        assert response.json() == {"error": "Book not found"}

    @pytest.mark.parametrize(
        "book_id",
        ["abc", "0", "-1", "01", "+1", "1.5", "1e3", "%20", "١٢٣", "9" * 19, "9" * 5000],
    )
    def test_an_id_that_can_never_exist_is_404(self, client, make_book, book_id):
        make_book()
        assert client.get(f"/books/{book_id}").status_code == 404


class TestUpdateBook:
    def test_replaces_the_book(self, client, make_book):
        book = make_book(**DUNE)
        replacement = {
            "title": "Dune Messiah",
            "author": "Frank Herbert",
            "year": 1969,
            "isbn": "978-0593098233",
        }

        response = client.put(f"/books/{book['id']}", json=replacement)

        assert response.status_code == 200
        assert response.json() == {"id": book["id"], **replacement}
        assert client.get(f"/books/{book['id']}").json() == response.json()

    def test_put_is_a_full_replacement_so_omitted_optional_fields_are_cleared(
        self, client, make_book
    ):
        book = make_book(**DUNE)

        response = client.put(
            f"/books/{book['id']}", json={"title": "Dune", "author": "Frank Herbert"}
        )

        assert response.json() == {
            "id": book["id"],
            "title": "Dune",
            "author": "Frank Herbert",
            "year": None,
            "isbn": None,
        }

    def test_the_whole_book_can_be_sent_back_including_its_id(self, client, make_book):
        book = make_book(**DUNE)
        book["year"] = 1966

        response = client.put(f"/books/{book['id']}", json=book)

        assert response.status_code == 200
        assert response.json() == book

    def test_the_id_in_the_body_cannot_move_the_book(self, client, make_book):
        first, second = make_book(title="First"), make_book(title="Second")

        response = client.put(
            f"/books/{first['id']}", json={"id": second["id"], "title": "X", "author": "Y"}
        )

        assert response.json()["id"] == first["id"]
        assert client.get(f"/books/{second['id']}").json() == second

    def test_only_the_addressed_book_changes(self, client, make_book):
        first, second = make_book(title="First"), make_book(title="Second")

        client.put(f"/books/{first['id']}", json={"title": "Changed", "author": "Someone"})

        assert client.get(f"/books/{second['id']}").json() == second

    def test_an_unknown_book_is_404_and_is_not_created(self, client):
        response = client.put("/books/42", json=DUNE)

        assert response.status_code == 404
        assert response.json() == {"error": "Book not found"}
        assert client.get("/books").json() == []

    @pytest.mark.parametrize("book_id", ["abc", "0", "-3", "9" * 25])
    def test_an_id_that_can_never_exist_is_404(self, client, book_id):
        assert client.put(f"/books/{book_id}", json=DUNE).status_code == 404

    @pytest.mark.parametrize("payload, field", INVALID_BOOKS)
    def test_an_invalid_book_is_rejected_with_400_and_the_stored_book_is_untouched(
        self, client, make_book, payload, field
    ):
        book = make_book(**DUNE)

        response = client.put(f"/books/{book['id']}", json=payload)

        assert response.status_code == 400
        assert field in response.json()["details"]
        assert client.get(f"/books/{book['id']}").json() == book

    def test_title_and_author_are_still_required(self, client, make_book):
        book = make_book(**DUNE)

        response = client.put(f"/books/{book['id']}", json={"year": 1999})

        assert response.status_code == 400
        assert set(response.json()["details"]) == {"title", "author"}

    def test_a_body_that_is_not_json_is_400(self, client, make_book):
        book = make_book()
        assert client.put(f"/books/{book['id']}", data="nope").status_code == 400


class TestDeleteBook:
    def test_deletes_the_book_and_returns_204_without_a_body(self, client, make_book):
        book = make_book(**DUNE)

        response = client.delete(f"/books/{book['id']}")

        assert response.status_code == 204
        assert response.body == b""
        assert client.get(f"/books/{book['id']}").status_code == 404
        assert client.get("/books").json() == []

    def test_deleting_twice_is_404_the_second_time(self, client, make_book):
        book = make_book()
        assert client.delete(f"/books/{book['id']}").status_code == 204

        response = client.delete(f"/books/{book['id']}")

        assert response.status_code == 404
        assert response.json() == {"error": "Book not found"}

    def test_other_books_are_untouched(self, client, make_book):
        keep, drop = make_book(title="Keep"), make_book(title="Drop")

        client.delete(f"/books/{drop['id']}")

        assert client.get("/books").json() == [keep]

    def test_a_deleted_id_is_never_handed_out_again(self, client, make_book):
        newest = make_book()
        client.delete(f"/books/{newest['id']}")

        assert make_book()["id"] > newest["id"]

    @pytest.mark.parametrize("book_id", ["42", "abc", "0", "9" * 25])
    def test_an_unknown_or_impossible_id_is_404(self, client, book_id):
        assert client.delete(f"/books/{book_id}").status_code == 404


class TestHealth:
    def test_reports_ok(self, client):
        response = client.get("/health")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert response.json() == {"status": "ok"}

    def test_reports_503_when_the_database_is_unavailable(self, client, repository, caplog):
        repository.close()

        with caplog.at_level(logging.ERROR, logger="bookapi.app"):
            response = client.get("/health")

        assert response.status_code == 503
        assert response.json()["status"] == "unavailable"
        assert "Health check failed" in caplog.text

    def test_needs_no_body_or_headers(self, client, make_book):
        make_book()
        assert client.get("/health").json() == {"status": "ok"}


class TestRouting:
    @pytest.mark.parametrize(
        "path", ["/", "/nope", "/book", "/books/1/extra", "/health/x", "/books//"]
    )
    def test_unknown_paths_are_404_json(self, client, path):
        response = client.get(path)

        assert response.status_code == 404
        assert response.headers["content-type"] == "application/json"
        assert response.json() == {"error": "Not found"}

    @pytest.mark.parametrize(
        "method, path, allow",
        [
            ("POST", "/health", "GET, HEAD, OPTIONS"),
            ("PUT", "/books", "GET, HEAD, OPTIONS, POST"),
            ("DELETE", "/books", "GET, HEAD, OPTIONS, POST"),
            ("PATCH", "/books", "GET, HEAD, OPTIONS, POST"),
            ("POST", "/books/1", "DELETE, GET, HEAD, OPTIONS, PUT"),
            ("PATCH", "/books/1", "DELETE, GET, HEAD, OPTIONS, PUT"),
        ],
    )
    def test_a_known_path_with_the_wrong_method_is_405_with_an_allow_header(
        self, client, method, path, allow
    ):
        response = client.request(method, path)

        assert response.status_code == 405
        assert response.headers["allow"] == allow
        assert response.json() == {"error": "Method not allowed"}

    def test_a_trailing_slash_is_the_same_resource(self, client):
        created = client.post("/books/", json=DUNE)
        assert created.status_code == 201
        book_id = created.json()["id"]

        assert client.get("/books/").json() == [created.json()]
        assert client.get(f"/books/{book_id}/").json() == created.json()
        assert client.put(f"/books/{book_id}/", json=DUNE).status_code == 200
        assert client.delete(f"/books/{book_id}/").status_code == 204
        assert client.get("/health/").status_code == 200

    def test_options_lists_the_allowed_methods(self, client):
        response = client.options("/books/1")

        assert response.status_code == 204
        assert response.headers["allow"] == "DELETE, GET, HEAD, OPTIONS, PUT"
        assert response.body == b""

    def test_head_mirrors_get_without_a_body(self, client):
        get, head = client.get("/health"), client.head("/health")

        assert head.status_code == 200
        assert head.body == b""
        assert head.headers["content-type"] == "application/json"
        assert head.headers["content-length"] == str(len(get.body))

    def test_head_of_a_missing_book_is_404_without_a_body(self, client):
        response = client.head("/books/1")

        assert response.status_code == 404
        assert response.body == b""

    def test_responses_forbid_content_type_sniffing(self, client):
        assert client.get("/health").headers["x-content-type-options"] == "nosniff"
        assert client.get("/nope").headers["x-content-type-options"] == "nosniff"


class TestRobustness:
    def test_an_unexpected_failure_is_a_generic_500_that_leaks_nothing(self, make_client, caplog):
        class Broken:
            def __getattr__(self, name):
                raise RuntimeError("secret internal detail")

        client = make_client(BookAPI(Broken()))

        with caplog.at_level(logging.ERROR, logger="bookapi.app"):
            response = client.get("/books")

        assert response.status_code == 500
        assert response.headers["content-type"] == "application/json"
        assert response.json() == {"error": "Internal server error"}
        assert "secret" not in response.text
        assert "secret internal detail" in caplog.text  # ...but the operator can still see it
        assert "GET '/books'" in caplog.text

    def test_concurrent_requests_are_all_handled(self, make_client, run_concurrently):
        repo = BookRepository(":memory:")  # private, so a stuck one is never touched again
        client = make_client(BookAPI(repo))
        results = []

        def worker(n):
            for i in range(25):
                results.append(
                    client.post("/books", json={"title": f"Book {n}-{i}", "author": "Someone"})
                )
                assert client.get("/books?author=someone").status_code == 200

        run_concurrently(worker, 8)

        try:
            assert {r.status_code for r in results} == {201}
            assert len({r.json()["id"] for r in results}) == 200
            assert len(client.get("/books").json()) == 200
        finally:
            repo.close()
