"""HTTP-level tests for every endpoint. Each test starts with an empty database."""

import datetime
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from books_api.app import MAX_BODY_BYTES, create_app

DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}
THIS_YEAR = datetime.date.today().year
NEXT_YEAR = THIS_YEAR + 1


def assert_problem(response, status, *invalid_fields):
    """Check ``response`` is an RFC 9457 problem with ``status``.

    If ``invalid_fields`` are given, they must be exactly the fields reported as invalid.
    """
    assert response.status_code == status, response.text
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["status"] == status
    assert body["title"] and body["detail"]
    if invalid_fields:
        assert {error["field"] for error in body["errors"]} == set(invalid_fields)
    return body


class TestHealth:
    def test_reports_ok(self, client):
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_reports_503_when_the_database_cannot_be_opened(self, client, db_path):
        # Swap the database file for a directory, which SQLite cannot open.
        db_path.unlink()
        db_path.mkdir()

        assert_problem(client.get("/health"), 503)

    def test_reports_503_like_every_endpoint_when_the_database_file_is_deleted(
        self, client, db_path
    ):
        db_path.unlink()

        assert_problem(client.get("/health"), 503)
        assert_problem(client.get("/books"), 503)

    def test_reports_503_like_every_endpoint_when_the_database_file_is_corrupt(
        self, client, db_path
    ):
        db_path.write_bytes(b"this is not an SQLite database" * 100)

        assert_problem(client.get("/health"), 503)
        assert_problem(client.get("/books"), 503)

    def test_app_refuses_to_start_with_an_unusable_database(self, tmp_path):
        with pytest.raises(sqlite3.Error):
            with TestClient(create_app(tmp_path)):  # a directory, not a file
                pass


class TestCreateBook:
    def test_returns_201_with_the_stored_book_and_its_location(self, client):
        response = client.post("/books", json=DUNE)

        assert response.status_code == 201
        book = response.json()
        assert book == {"id": book["id"], **DUNE}
        assert isinstance(book["id"], int)
        assert response.headers["location"].endswith(f"/books/{book['id']}")
        assert client.get(response.headers["location"]).json() == book

    def test_only_title_and_author_are_required(self, client):
        response = client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})

        assert response.status_code == 201
        assert response.json()["year"] is None
        assert response.json()["isbn"] is None

    def test_trims_whitespace_and_stores_a_blank_isbn_as_null(self, client):
        response = client.post(
            "/books", json={"title": "  Dune ", "author": "\tFrank Herbert\n", "isbn": "  "}
        )

        book = response.json()
        assert (book["title"], book["author"], book["isbn"]) == ("Dune", "Frank Herbert", None)

    def test_ignores_unknown_fields_and_a_client_supplied_id(self, client):
        response = client.post("/books", json={**DUNE, "id": 42, "genre": "science fiction"})

        assert response.status_code == 201
        assert response.json() == {"id": 1, **DUNE}

    @pytest.mark.parametrize("year", [1, THIS_YEAR])
    def test_accepts_values_at_the_limits(self, client, year):
        book = {"title": "T" * 500, "author": "A" * 500, "year": year, "isbn": "9" * 32}

        response = client.post("/books", json=book)

        assert response.status_code == 201
        assert response.json() == {"id": response.json()["id"], **book}

    def test_a_malformed_host_header_still_creates_exactly_one_book(self, client):
        response = client.post("/books", json=DUNE, headers={"Host": "[1:2]"})

        assert response.status_code == 201
        assert response.headers["location"] == f"/books/{response.json()['id']}"
        assert len(client.get("/books").json()) == 1

    def test_accepts_a_json_content_type_with_parameters(self, client):
        response = client.post(
            "/books",
            content=json.dumps(DUNE).encode(),
            headers={"Content-Type": "application/json; charset=utf-8"},
        )

        assert response.status_code == 201

    @pytest.mark.parametrize(
        ("payload", "invalid_field"),
        [
            pytest.param({"author": "Frank Herbert"}, "title", id="missing title"),
            pytest.param({"title": "Dune"}, "author", id="missing author"),
            pytest.param({**DUNE, "title": "   "}, "title", id="blank title"),
            pytest.param({**DUNE, "author": ""}, "author", id="empty author"),
            pytest.param({**DUNE, "title": None}, "title", id="null title"),
            pytest.param({**DUNE, "title": 1984}, "title", id="numeric title"),
            pytest.param({**DUNE, "title": "x" * 501}, "title", id="title too long"),
            pytest.param({**DUNE, "title": "\u0000Dune"}, "title", id="NUL in title"),
            pytest.param({**DUNE, "author": "Frank\x1bHerbert"}, "author", id="escape in author"),
            pytest.param({**DUNE, "isbn": "978\t0441172719"}, "isbn", id="tab inside isbn"),
            pytest.param({**DUNE, "year": "1965"}, "year", id="year as string"),
            pytest.param({**DUNE, "year": True}, "year", id="year as boolean"),
            pytest.param({**DUNE, "year": 1965.5}, "year", id="fractional year"),
            pytest.param({**DUNE, "year": 0}, "year", id="year zero"),
            pytest.param({**DUNE, "year": NEXT_YEAR}, "year", id="future year"),
            pytest.param({**DUNE, "isbn": 9780441172719}, "isbn", id="numeric isbn"),
            pytest.param({**DUNE, "isbn": "9" * 33}, "isbn", id="isbn too long"),
        ],
    )
    def test_rejects_an_invalid_book_and_stores_nothing(self, client, payload, invalid_field):
        assert_problem(client.post("/books", json=payload), 400, invalid_field)
        assert client.get("/books").json() == []

    def test_reports_every_invalid_field_at_once(self, client):
        response = client.post("/books", json={"year": "soon"})

        assert_problem(response, 400, "title", "author", "year")

    def test_rejects_malformed_json(self, client):
        response = client.post(
            "/books",
            content=b'{"title": "Dune",',
            headers={"Content-Type": "application/json"},
        )

        body = assert_problem(response, 400)
        assert body["detail"].startswith("Request body is not valid JSON")

    @pytest.mark.parametrize("body", [b"[]", b'"Dune"', b"42"])
    def test_rejects_json_that_is_not_an_object(self, client, body):
        response = client.post("/books", content=body, headers={"Content-Type": "application/json"})

        problem = assert_problem(response, 400, "body")
        assert problem["errors"][0]["message"] == "Request body must be a JSON object"

    def test_requires_a_body(self, client):
        problem = assert_problem(client.post("/books"), 400, "body")
        assert problem["errors"][0]["message"] == "Request body is required"

    @pytest.mark.parametrize(
        "content_type", [None, "text/plain", "application/x-www-form-urlencoded"]
    )
    def test_answers_415_to_a_body_not_declared_as_json(self, client, content_type):
        headers = {"Content-Type": content_type} if content_type else {}
        response = client.post("/books", content=json.dumps(DUNE).encode(), headers=headers)

        assert_problem(response, 415)
        assert client.get("/books").json() == []


class TestListBooks:
    def test_an_empty_collection_is_an_empty_list(self, client):
        response = client.get("/books")

        assert response.status_code == 200
        assert response.json() == []

    def test_lists_every_book_in_the_order_added(self, client, add_book):
        added = [add_book(title=title) for title in ("Dune", "Emma", "Ulysses")]

        assert client.get("/books").json() == added

    @pytest.mark.parametrize(
        ("author", "expected_titles"),
        [
            ("Frank Herbert", ["Dune", "Dune Messiah"]),
            ("frank herbert", ["Dune", "Dune Messiah"]),
            ("HERB", ["Dune", "Dune Messiah"]),
            ("austen", ["Emma"]),
            ("Tolkien", []),
        ],
    )
    def test_filters_by_author_ignoring_case_and_matching_part_of_the_name(
        self, client, add_book, author, expected_titles
    ):
        add_book(title="Dune", author="Frank Herbert")
        add_book(title="Emma", author="Jane Austen")
        add_book(title="Dune Messiah", author="Frank Herbert")

        response = client.get("/books", params={"author": author})

        assert response.status_code == 200
        assert [book["title"] for book in response.json()] == expected_titles

    def test_author_filter_ignores_case_beyond_ascii(self, client, add_book):
        add_book(title="Nana", author="Émile Zola")
        add_book(title="Paare, Passanten", author="Botho Strauß")

        def titles(author):
            return [book["title"] for book in client.get("/books", params={"author": author}).json()]

        assert titles("ÉMILE") == ["Nana"]
        assert titles("STRAUSS") == ["Paare, Passanten"]

    def test_author_filter_matches_however_an_accent_is_encoded(self, client, add_book):
        add_book(title="Nana", author="E\u0301mile Zola")  # E + COMBINING ACUTE ACCENT

        response = client.get("/books", params={"author": "\u00c9mile"})  # precomposed É

        assert [book["title"] for book in response.json()] == ["Nana"]

    def test_author_filter_is_plain_text_not_a_pattern(self, client, add_book):
        add_book(author="Frank Herbert")

        assert client.get("/books", params={"author": "%"}).json() == []
        assert client.get("/books", params={"author": "Fr_nk"}).json() == []

    def test_a_blank_author_filter_lists_every_book(self, client, add_book):
        add_book()
        add_book(title="Emma", author="Jane Austen")

        assert len(client.get("/books", params={"author": "  "}).json()) == 2


class TestGetBook:
    def test_returns_the_book(self, client, add_book):
        book = add_book()

        response = client.get(f"/books/{book['id']}")

        assert response.status_code == 200
        assert response.json() == book

    def test_an_unknown_id_is_404(self, client):
        assert_problem(client.get("/books/999"), 404)

    @pytest.mark.parametrize(
        "book_id",
        [
            "abc",
            "0",
            "-1",
            "1.0",
            "٣",  # ARABIC-INDIC DIGIT THREE: int() accepts it, but it is not "3"
            "9223372036854775808",  # one past SQLite's largest integer id
            "9" * 5000,  # beyond Python's int() digit limit
        ],
    )
    def test_an_id_that_cannot_exist_is_404(self, client, add_book, book_id):
        for _ in range(3):
            add_book()

        assert_problem(client.get(f"/books/{book_id}"), 404)


class TestReplaceBook:
    def test_replaces_every_field_and_persists(self, client, add_book):
        book = add_book()
        new = {"title": "Children of Dune", "author": "F. Herbert", "year": 1976, "isbn": "978-0593098240"}

        response = client.put(f"/books/{book['id']}", json=new)

        assert response.status_code == 200
        assert response.json() == {"id": book["id"], **new}
        assert client.get(f"/books/{book['id']}").json() == {"id": book["id"], **new}

    def test_clears_optional_fields_that_are_left_out(self, client, add_book):
        book = add_book()

        response = client.put(f"/books/{book['id']}", json={"title": "Dune", "author": "Frank Herbert"})

        assert response.status_code == 200
        assert (response.json()["year"], response.json()["isbn"]) == (None, None)

    def test_ignores_an_id_in_the_body(self, client, add_book):
        first = add_book()
        second = add_book(title="Emma", author="Jane Austen")

        response = client.put(f"/books/{first['id']}", json={**DUNE, "id": second["id"]})

        assert response.json()["id"] == first["id"]
        assert client.get(f"/books/{second['id']}").json() == second

    @pytest.mark.parametrize(
        ("payload", "invalid_field"),
        [
            pytest.param({"title": "Dune Messiah"}, "author", id="missing author"),
            pytest.param({**DUNE, "title": " "}, "title", id="blank title"),
            pytest.param({**DUNE, "year": "1969"}, "year", id="year as string"),
        ],
    )
    def test_is_validated_like_create_and_leaves_the_book_unchanged(
        self, client, add_book, payload, invalid_field
    ):
        book = add_book()

        assert_problem(client.put(f"/books/{book['id']}", json=payload), 400, invalid_field)
        assert client.get(f"/books/{book['id']}").json() == book

    def test_answers_415_to_a_body_not_declared_as_json(self, client, add_book):
        book = add_book()

        response = client.put(
            f"/books/{book['id']}",
            content=json.dumps(DUNE).encode(),
            headers={"Content-Type": "text/plain"},
        )

        assert_problem(response, 415)

    def test_an_unknown_id_is_404_and_creates_nothing(self, client):
        assert_problem(client.put("/books/999", json=DUNE), 404)
        assert client.get("/books").json() == []


class TestDeleteBook:
    def test_returns_204_and_removes_only_that_book(self, client, add_book):
        book = add_book()
        other = add_book(title="Emma", author="Jane Austen")

        response = client.delete(f"/books/{book['id']}")

        assert response.status_code == 204
        assert response.content == b""
        assert_problem(client.get(f"/books/{book['id']}"), 404)
        assert client.get("/books").json() == [other]

    def test_deleting_again_is_404(self, client, add_book):
        book = add_book()
        client.delete(f"/books/{book['id']}")

        assert_problem(client.delete(f"/books/{book['id']}"), 404)

    def test_an_unknown_id_is_404(self, client):
        assert_problem(client.delete("/books/999"), 404)

    def test_the_id_of_a_deleted_book_is_never_reused(self, client, add_book):
        book = add_book()
        client.delete(f"/books/{book['id']}")

        assert add_book()["id"] > book["id"]


class TestErrors:
    def test_an_unknown_route_is_404(self, client):
        assert_problem(client.get("/authors"), 404)

    @pytest.mark.parametrize(
        ("method", "path", "allow"),
        [
            ("PATCH", "/books/1", "DELETE, GET, PUT"),
            ("DELETE", "/books", "GET, POST"),
            ("POST", "/health", "GET"),
        ],
    )
    def test_an_unsupported_method_is_405_and_lists_every_allowed_method(
        self, client, method, path, allow
    ):
        response = client.request(method, path)

        assert_problem(response, 405)
        assert response.headers["allow"] == allow

    def test_a_body_at_the_size_limit_is_accepted(self, client):
        body = json.dumps(DUNE).encode().rjust(MAX_BODY_BYTES)  # leading spaces are valid JSON

        response = client.post("/books", content=body, headers={"Content-Type": "application/json"})

        assert response.status_code == 201

    def test_a_body_over_the_size_limit_is_413(self, client):
        body = json.dumps(DUNE).encode().rjust(MAX_BODY_BYTES + 1)

        response = client.post("/books", content=body, headers={"Content-Type": "application/json"})

        assert_problem(response, 413)
        assert client.get("/books").json() == []

    def test_a_declared_length_over_the_limit_is_refused_before_reading(self, client):
        response = client.post(
            "/books",
            content=json.dumps(DUNE).encode(),
            headers={"Content-Type": "application/json", "Content-Length": str(MAX_BODY_BYTES + 1)},
        )

        assert_problem(response, 413)

    def test_a_streamed_body_over_the_size_limit_is_413(self, client):
        # No Content-Length: the body is counted as it arrives.
        chunks = (b" " * 65536 for _ in range(MAX_BODY_BYTES // 65536 + 1))

        response = client.post("/books", content=chunks, headers={"Content-Type": "application/json"})

        assert "content-length" not in response.request.headers
        assert_problem(response, 413)

    def test_an_unexpected_error_is_a_generic_500(self, db_path, monkeypatch):
        app = create_app(db_path)

        def fail(*args, **kwargs):
            raise RuntimeError("internal detail that must not leak")

        monkeypatch.setattr(app.state.repository, "list_books", fail)
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/books")

        assert_problem(response, 500)
        assert "internal detail" not in response.text

    def test_the_openapi_document_describes_problem_responses_not_422(self, client):
        paths = client.get("/openapi.json").json()["paths"]

        for operations in paths.values():
            for operation in operations.values():
                assert "4XX" in operation["responses"]
                assert "422" not in operation["responses"]


def test_the_database_path_comes_from_the_argument_then_the_environment(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("BOOKS_API_DB", str(tmp_path / "env.db"))

    assert create_app().state.repository.path == str(tmp_path / "env.db")
    assert create_app(tmp_path / "arg.db").state.repository.path == str(tmp_path / "arg.db")


def test_an_in_memory_database_is_refused():
    # Each operation opens a new connection, which would see a new, empty database.
    with pytest.raises(ValueError, match="database file is required"):
        create_app(":memory:")


def test_books_survive_an_application_restart(db_path):
    with TestClient(create_app(db_path)) as client:
        book = client.post("/books", json=DUNE).json()

    with TestClient(create_app(db_path)) as client:
        assert client.get(f"/books/{book['id']}").json() == book
