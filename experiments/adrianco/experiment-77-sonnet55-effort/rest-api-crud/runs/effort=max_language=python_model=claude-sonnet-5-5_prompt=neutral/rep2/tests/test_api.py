"""Integration tests: each endpoint exercised through the WSGI interface.

The application, validation and a real (in-memory) SQLite database all take part;
only the socket layer is skipped (see ``test_server.py`` for that).
"""

from __future__ import annotations

import json
import logging
import socket

import pytest
from support import WSGIClient, book_payload

from bookapi.app import DEFAULT_DATABASE, create_app
from bookapi.web import MAX_BODY_BYTES


@pytest.fixture
def create(client):
    """Create a book through the API and return its JSON representation."""

    def _create(**overrides):
        response = client.post("/books", json=book_payload(**overrides))
        assert response.status == 201, response.body
        return response.json()

    return _create


def test_full_book_lifecycle(client):
    """Create, list, filter, read, update and delete: every requirement in one story."""
    assert client.get("/health").status == 200

    created = client.post("/books", json=book_payload())
    assert created.status == 201
    book = created.json()
    assert book == {"id": 1, **book_payload()}

    other = client.post("/books", json=book_payload(title="Emma", author="Jane Austen")).json()
    assert client.get("/books").json() == [book, other]
    assert client.get("/books?author=Jane%20Austen").json() == [other]
    assert client.get("/books/1").json() == book

    changed = book_payload(title="Refactored", year=2000)
    assert client.put("/books/1", json=changed).json() == {"id": 1, **changed}

    assert client.delete("/books/1").status == 204
    assert client.get("/books/1").status == 404
    assert client.get("/books").json() == [other]


class TestCreateApp:
    """``create_app`` is the factory for external WSGI servers."""

    @pytest.fixture(autouse=True)
    def clean_environment(self, monkeypatch, tmp_path):
        monkeypatch.delenv("BOOKS_DB", raising=False)
        monkeypatch.chdir(tmp_path)  # keeps any default-path file out of the project

    def build(self, *args):
        app = create_app(*args)
        try:
            assert WSGIClient(app).get("/health").status == 200
        finally:
            app.repository.close()

    def test_uses_the_given_path(self, tmp_path):
        self.build(tmp_path / "given.db")
        assert (tmp_path / "given.db").exists()

    def test_falls_back_to_the_environment_variable(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BOOKS_DB", str(tmp_path / "from-env.db"))
        self.build()
        assert (tmp_path / "from-env.db").exists()

    def test_defaults_to_books_db_in_the_working_directory(self, tmp_path):
        self.build()
        assert (tmp_path / DEFAULT_DATABASE).exists()

    def test_an_empty_environment_variable_counts_as_unset(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BOOKS_DB", "")
        self.build()
        assert (tmp_path / DEFAULT_DATABASE).exists()

    def test_an_empty_path_is_refused_rather_than_silently_not_saving(self):
        with pytest.raises(ValueError, match="must not be empty"):
            create_app("")


class TestHealth:
    def test_reports_ok(self, client):
        response = client.get("/health")
        assert response.status == 200
        assert response.headers["content-type"] == "application/json"
        assert response.json() == {"status": "ok"}

    def test_reports_unavailable_when_the_database_is_down(self, client, repository, caplog):
        repository.close()
        with caplog.at_level(logging.ERROR):
            response = client.get("/health")
        assert response.status == 503
        assert response.json() == {"status": "unavailable"}
        assert "Health check failed" in caplog.text


class TestCreateBook:
    def test_creates_a_book(self, client):
        response = client.post("/books", json=book_payload())
        assert response.status == 201
        assert response.headers["content-type"] == "application/json"
        assert response.headers["location"] == "/books/1"
        assert response.json() == {"id": 1, **book_payload()}

    def test_the_new_book_can_be_fetched_from_its_location(self, client, create):
        created = create()
        response = client.post("/books", json=book_payload(title="Second"))
        assert client.get(response.headers["location"]).json() == response.json()
        assert client.get("/books/1").json() == created

    def test_only_title_and_author_are_required(self, client):
        response = client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})
        assert response.status == 201
        assert response.json() == {
            "id": 1,
            "title": "Dune",
            "author": "Frank Herbert",
            "year": None,
            "isbn": None,
        }

    def test_input_is_trimmed(self, client):
        response = client.post("/books", json=book_payload(title="  Dune ", author=" F. Herbert\t"))
        assert (response.json()["title"], response.json()["author"]) == ("Dune", "F. Herbert")

    def test_ids_are_unique_and_increasing(self, create):
        assert [create(title=f"Book {n}")["id"] for n in range(3)] == [1, 2, 3]

    def test_unicode_survives_the_round_trip_as_utf8(self, client):
        payload = book_payload(title="吾輩は猫である", author="夏目 漱石")
        response = client.post("/books", json=payload)
        assert response.json() == {"id": 1, **payload}
        assert "吾輩は猫である".encode() in response.body  # raw UTF-8, not \u-escaped
        assert client.get("/books/1").json()["author"] == "夏目 漱石"

    def test_unknown_fields_and_a_client_supplied_id_are_ignored(self, client):
        response = client.post("/books", json=book_payload(id=99, rating=5))
        assert response.json() == {"id": 1, **book_payload()}

    def test_location_respects_where_the_app_is_mounted(self, client):
        response = client.post("/books", json=book_payload(), environ={"SCRIPT_NAME": "/api/v1"})
        assert response.headers["location"] == "/api/v1/books/1"

    def test_a_content_type_header_is_not_required(self, client):
        # `curl -d` labels its body application/x-www-form-urlencoded.
        response = client.post(
            "/books",
            data=json.dumps(book_payload()).encode(),
            environ={"CONTENT_TYPE": "application/x-www-form-urlencoded"},
        )
        assert response.status == 201

    def test_a_body_exactly_at_the_size_limit_is_accepted(self, client):
        overhead = len(json.dumps({"title": "T", "author": "A", "pad": ""}))
        body = json.dumps({"title": "T", "author": "A", "pad": "x" * (MAX_BODY_BYTES - overhead)})
        assert len(body) == MAX_BODY_BYTES
        assert client.post("/books", data=body.encode()).status == 201


class TestCreateBookValidation:
    @pytest.mark.parametrize("field", ["title", "author"])
    def test_a_missing_required_field_is_a_400(self, client, field):
        payload = book_payload()
        del payload[field]
        response = client.post("/books", json=payload)
        assert response.status == 400
        assert response.headers["content-type"] == "application/json"
        assert response.json() == {
            "error": f"Validation failed: {field} is required",
            "details": {field: f"{field} is required"},
        }

    @pytest.mark.parametrize("field", ["title", "author"])
    @pytest.mark.parametrize("value", ["", "   ", None], ids=repr)
    def test_a_blank_required_field_is_a_400(self, client, field, value):
        response = client.post("/books", json=book_payload(**{field: value}))
        assert response.status == 400
        assert response.json()["details"] == {field: f"{field} is required"}

    def test_every_problem_is_reported_at_once(self, client):
        response = client.post("/books", json={"year": "nineteen", "isbn": 7})
        assert response.status == 400
        assert set(response.json()["details"]) == {"title", "author", "year", "isbn"}
        assert "title is required" in response.json()["error"]

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("title", 5),
            ("author", ["A"]),
            ("year", "1999"),
            ("year", 1999.5),
            ("year", True),
            ("year", 0),
            ("year", 10000),
            ("isbn", 9780441172719),
            ("title", "x" * 256),
        ],
        ids=lambda v: repr(v)[:20],
    )
    def test_invalid_values_are_a_400(self, client, field, value):
        response = client.post("/books", json=book_payload(**{field: value}))
        assert response.status == 400
        assert list(response.json()["details"]) == [field]

    def test_a_rejected_book_is_not_stored(self, client):
        assert client.post("/books", json=book_payload(title="")).status == 400
        assert client.get("/books").json() == []

    @pytest.mark.parametrize(
        "body",
        [b"{", b"not json", b"   ", b"\xff\xfe\x00", b'{"title": "x",}', b"{'title': 'x'}"],
        ids=repr,
    )
    def test_malformed_json_is_a_400(self, client, body):
        response = client.post("/books", data=body)
        assert response.status == 400
        assert response.json() == {"error": "Request body must be valid JSON"}

    def test_a_missing_body_is_a_400(self, client):
        response = client.post("/books")
        assert response.status == 400
        assert response.json() == {"error": "Request body is required"}

    @pytest.mark.parametrize("payload", [[], [book_payload()], "text", 42, None, True], ids=repr)
    def test_a_body_that_is_not_a_json_object_is_a_400(self, client, payload):
        response = client.post("/books", json=payload)
        assert response.status == 400
        assert response.json()["details"] == {"body": "body must be a JSON object"}

    def test_deeply_nested_json_is_a_400_not_a_crash(self, client):
        # Well-formed, and under the size limit. Older Pythons raise RecursionError
        # while parsing this (-> "valid JSON" error); newer ones parse it happily and
        # the validator then refuses the array. Either way: 400, never a 500.
        response = client.post("/books", data=b"[" * 30_000 + b"]" * 30_000)
        assert response.status == 400

    def test_an_oversized_body_is_a_413(self, client):
        response = client.post("/books", data=b" " * (MAX_BODY_BYTES + 1))
        assert response.status == 413
        assert str(MAX_BODY_BYTES) in response.json()["error"]

    @pytest.mark.parametrize(
        "length", [str(MAX_BODY_BYTES + 1), "99999", "1" + "0" * 30, "9" * 5000], ids=len
    )
    def test_a_declared_length_over_the_limit_is_a_413_without_reading(self, app, length):
        raw = WSGIClient(app, validate=False)  # wsgiref.validate would choke on these itself
        response = raw.post("/books", environ={"CONTENT_LENGTH": length})
        assert response.status == 413

    @pytest.mark.parametrize("length", ["abc", "-1", "+29", "1_0", "1.5", "0x10", "٣"], ids=ascii)
    def test_a_malformed_content_length_is_a_400(self, app, length):
        raw = WSGIClient(app, validate=False)  # wsgiref.validate refuses such an environ
        response = raw.post("/books", data=b"{}", environ={"CONTENT_LENGTH": length})
        assert response.status == 400
        assert response.json() == {"error": "Invalid Content-Length header"}

    def test_padding_around_the_content_length_is_tolerated(self, app):
        body = json.dumps(book_payload()).encode()
        raw = WSGIClient(app, validate=False)
        response = raw.post("/books", data=body, environ={"CONTENT_LENGTH": f" {len(body):09d} "})
        assert response.status == 201

    def test_a_chunked_body_is_a_411_because_wsgi_cannot_read_one_portably(self, client):
        response = client.post("/books", environ={"HTTP_TRANSFER_ENCODING": "chunked"})
        assert response.status == 411
        assert "Content-Length" in response.json()["error"]

    @pytest.mark.parametrize(
        "failure", [socket.timeout("timed out"), ConnectionResetError()], ids=repr
    )
    def test_a_body_that_cannot_be_read_is_a_408(self, app, failure):
        class DeadInput:
            def read(self, size=-1):
                raise failure

        raw = WSGIClient(app, validate=False)
        response = raw.post("/books", environ={"CONTENT_LENGTH": "10", "wsgi.input": DeadInput()})
        assert response.status == 408
        assert response.json() == {"error": "The request body could not be read in time"}


class TestListBooks:
    def test_an_empty_collection_is_an_empty_array(self, client):
        response = client.get("/books")
        assert response.status == 200
        assert response.headers["content-type"] == "application/json"
        assert response.json() == []

    def test_lists_every_book_in_creation_order(self, client, create):
        books = [create(title=f"Book {n}") for n in range(3)]
        response = client.get("/books")
        assert response.status == 200
        assert response.json() == books

    def test_filters_by_author(self, client, create):
        orwell = [
            create(title="1984", author="George Orwell"),
            create(title="Animal Farm", author="George Orwell"),
        ]
        create(title="Emma", author="Jane Austen")
        assert client.get("/books?author=George%20Orwell").json() == orwell

    @pytest.mark.parametrize(
        "query",
        [
            "author=George%20Orwell",
            "author=George+Orwell",
            "author=george%20orwell",
            "author=%20George%20Orwell%20",
            "colour=red&author=George+Orwell",
        ],
    )
    def test_author_filter_accepts_common_encodings_and_ignores_case(self, client, create, query):
        orwell = create(title="1984", author="George Orwell")
        create(title="Emma", author="Jane Austen")
        assert client.get(f"/books?{query}").json() == [orwell]

    def test_an_author_with_no_books_gives_an_empty_array(self, client, create):
        create()
        response = client.get("/books?author=Nobody")
        assert (response.status, response.json()) == (200, [])

    def test_the_author_must_match_in_full(self, client, create):
        create(author="George Orwell")
        assert client.get("/books?author=Orwell").json() == []

    @pytest.mark.parametrize("query", ["author=", "author=%20%20", "author", "colour=red"])
    def test_a_blank_or_unrelated_query_lists_everything(self, client, create, query):
        books = [create(author="A"), create(author="B")]
        assert client.get(f"/books?{query}").json() == books

    def test_only_the_first_author_parameter_is_used(self, client, create):
        first = create(author="A")
        create(author="B")
        assert client.get("/books?author=A&author=B").json() == [first]

    def test_non_ascii_authors_can_be_filtered_percent_encoded(self, client, create):
        garcia = create(author="Gabriel García Márquez")
        response = client.get("/books?author=GABRIEL%20GARC%C3%8DA%20M%C3%81RQUEZ")
        assert response.json() == [garcia]

    def test_non_ascii_authors_can_be_filtered_without_percent_encoding(self, client, create):
        # curl sends UTF-8 as-is; PEP 3333 then presents those bytes as latin-1 text.
        garcia = create(author="García")
        raw_query = "author=" + "García".encode().decode("latin-1")
        assert client.get("/books?" + raw_query).json() == [garcia]

    def test_accents_match_however_they_are_composed(self, client, create):
        zoe = create(author="Zo\xeb")  # e-diaeresis as a single character
        assert client.get("/books?author=Zoe%CC%88").json() == [zoe]  # "e" + combining diaeresis

    def test_a_lone_surrogate_in_the_query_matches_nothing_instead_of_failing(self, client, create):
        # A server that decodes the query itself (instead of as latin-1) can produce one.
        create()
        response = client.get("/books?author=bad\udcff")
        assert (response.status, response.json()) == (200, [])

    @pytest.mark.parametrize("author", ["Zo\xeb", "\N{GREEK CAPITAL LETTER OMEGA}mega"], ids=ascii)
    def test_a_server_that_already_decoded_the_query_string_is_tolerated(
        self, client, create, author
    ):
        # Not every WSGI server follows PEP 3333's latin-1 convention.
        book = create(author=author)
        assert client.get(f"/books?author={author}").json() == [book]

    def test_the_filter_cannot_be_used_for_sql_injection(self, client, create):
        create()
        response = client.get("/books?author=x'%20OR%20'1'='1")
        assert (response.status, response.json()) == (200, [])
        assert len(client.get("/books").json()) == 1


class TestGetBook:
    def test_returns_the_book(self, client, create):
        created = create()
        response = client.get(f"/books/{created['id']}")
        assert response.status == 200
        assert response.headers["content-type"] == "application/json"
        assert response.json() == created

    def test_selects_the_right_book_among_many(self, client, create):
        books = [create(title=f"Book {n}") for n in range(3)]
        assert client.get("/books/2").json() == books[1]

    def test_an_unknown_id_is_a_404(self, client, create):
        create()
        response = client.get("/books/42")
        assert response.status == 404
        assert response.headers["content-type"] == "application/json"
        assert response.json() == {"error": "Book not found"}

    @pytest.mark.parametrize(
        "book_id",
        ["abc", "-1", "1.5", "1e3", "0x1", "1%20", "١", "１"],  # last two: non-ASCII digit one
        ids=repr,
    )
    def test_an_id_that_is_not_a_positive_integer_is_a_404(self, client, create, book_id):
        create()  # book 1 exists, so anything that int() would read as 1 would wrongly succeed
        assert client.get(f"/books/{book_id}").status == 404

    @pytest.mark.parametrize(
        "book_id",
        ["0", "9223372036854775807", "9223372036854775808", "9" * 19, "9" * 20, "9" * 5000],
        ids=lambda v: v[:24],
    )
    def test_ids_beyond_anything_storable_are_a_404_not_an_error(self, client, book_id):
        response = client.get(f"/books/{book_id}")
        assert response.status == 404


class TestUpdateBook:
    def test_replaces_the_book(self, client, create):
        created = create()
        new = {
            "title": "The Pragmatic Programmer, 20th Anniversary Edition",
            "author": "David Thomas, Andrew Hunt",
            "year": 2019,
            "isbn": "978-0135957059",
        }
        response = client.put(f"/books/{created['id']}", json=new)
        assert response.status == 200
        assert response.headers["content-type"] == "application/json"
        assert response.json() == {"id": created["id"], **new}
        assert client.get(f"/books/{created['id']}").json() == response.json()

    def test_omitted_optional_fields_are_cleared(self, client, create):
        # PUT replaces the whole resource, so it is not a partial update.
        created = create()
        response = client.put(f"/books/{created['id']}", json={"title": "New", "author": "Someone"})
        assert response.json() == {
            "id": created["id"],
            "title": "New",
            "author": "Someone",
            "year": None,
            "isbn": None,
        }

    def test_a_fetched_book_can_be_sent_straight_back(self, client, create):
        created = create()
        response = client.put(f"/books/{created['id']}", json=created)
        assert (response.status, response.json()) == (200, created)

    def test_other_books_are_untouched(self, client, create):
        first, second = create(title="First"), create(title="Second")
        client.put(f"/books/{first['id']}", json=book_payload(title="Changed"))
        assert client.get(f"/books/{second['id']}").json() == second

    def test_the_id_cannot_be_changed_through_the_body(self, client, create):
        created = create()
        response = client.put(f"/books/{created['id']}", json=book_payload(id=999))
        assert response.json()["id"] == created["id"]
        assert client.get("/books/999").status == 404

    def test_an_unknown_id_is_a_404(self, client):
        response = client.put("/books/42", json=book_payload())
        assert response.status == 404
        assert response.json() == {"error": "Book not found"}
        assert client.get("/books").json() == []  # PUT does not create

    @pytest.mark.parametrize("field", ["title", "author"])
    def test_required_fields_are_still_required(self, client, create, field):
        created = create()
        payload = book_payload()
        del payload[field]
        response = client.put(f"/books/{created['id']}", json=payload)
        assert response.status == 400
        assert response.json()["details"] == {field: f"{field} is required"}

    @pytest.mark.parametrize(
        "changes", [{"title": ""}, {"author": "   "}, {"year": "2000"}, {"year": 0}, {"isbn": 5}]
    )
    def test_invalid_data_is_a_400_and_changes_nothing(self, client, create, changes):
        created = create()
        response = client.put(f"/books/{created['id']}", json=book_payload(**changes))
        assert response.status == 400
        assert client.get(f"/books/{created['id']}").json() == created

    def test_malformed_and_missing_bodies_are_a_400(self, client, create):
        created = create()
        assert client.put(f"/books/{created['id']}", data=b"{nope").status == 400
        assert client.put(f"/books/{created['id']}").status == 400
        assert client.get(f"/books/{created['id']}").json() == created


class TestDeleteBook:
    def test_deletes_the_book(self, client, create):
        created = create()
        response = client.delete(f"/books/{created['id']}")
        assert response.status == 204
        assert response.body == b""
        assert "content-type" not in response.headers
        assert client.get(f"/books/{created['id']}").status == 404
        assert client.get("/books").json() == []

    def test_only_the_addressed_book_is_deleted(self, client, create):
        first, second, third = create(title="1"), create(title="2"), create(title="3")
        client.delete(f"/books/{second['id']}")
        assert client.get("/books").json() == [first, third]

    def test_an_unknown_id_is_a_404(self, client):
        response = client.delete("/books/42")
        assert response.status == 404
        assert response.json() == {"error": "Book not found"}

    def test_deleting_twice_is_a_404_the_second_time(self, client, create):
        created = create()
        assert client.delete(f"/books/{created['id']}").status == 204
        assert client.delete(f"/books/{created['id']}").status == 404

    def test_a_deleted_id_is_never_handed_out_again(self, client, create):
        created = create()
        client.delete(f"/books/{created['id']}")
        assert create()["id"] == created["id"] + 1


class TestRouting:
    @pytest.mark.parametrize(
        "path", ["/", "/nope", "/books/1/extra", "/health/x", "/Books", "/book"]
    )
    def test_an_unknown_path_is_a_json_404(self, client, path):
        response = client.get(path)
        assert response.status == 404
        assert response.headers["content-type"] == "application/json"
        assert response.json() == {"error": "Not found"}

    @pytest.mark.parametrize(
        ("method", "path", "allow"),
        [
            ("DELETE", "/books", "GET, HEAD, POST"),
            ("PUT", "/books", "GET, HEAD, POST"),
            ("PATCH", "/books", "GET, HEAD, POST"),
            ("POST", "/books/1", "DELETE, GET, HEAD, PUT"),
            ("PATCH", "/books/1", "DELETE, GET, HEAD, PUT"),
            ("POST", "/health", "GET, HEAD"),
            ("DELETE", "/health", "GET, HEAD"),
            ("OPTIONS", "/books", "GET, HEAD, POST"),
        ],
    )
    def test_a_wrong_method_is_a_405_listing_the_allowed_ones(self, client, method, path, allow):
        response = client.request(method, path)
        assert response.status == 405
        assert response.headers["allow"] == allow
        assert response.headers["content-type"] == "application/json"
        assert response.json() == {"error": "Method not allowed"}

    @pytest.mark.parametrize("path", ["/books/", "/books//"])
    def test_trailing_slashes_are_tolerated(self, client, create, path):
        create()
        assert client.get(path).status == 200
        assert client.post(path, json=book_payload()).status == 201

    def test_a_trailing_slash_works_on_a_single_book_and_health(self, client, create):
        create()
        assert client.get("/books/1/").status == 200
        assert client.get("/health/").status == 200

    def test_method_names_are_case_sensitive(self, app):
        raw = WSGIClient(app, validate=False)  # wsgiref.validate warns about unknown methods
        assert raw.request("get", "/health").status == 405

    def test_head_mirrors_get_but_sends_no_body(self, client, create):
        create()
        for path in ("/health", "/books", "/books/1", "/books/2"):
            get = client.get(path)
            head = client.request("HEAD", path)
            assert head.status == get.status, path
            assert head.body == b"", path
            assert head.headers["content-length"] == str(len(get.body)), path
            assert head.headers["content-type"] == get.headers["content-type"], path

    def test_head_of_something_missing_is_a_404(self, client):
        assert client.request("HEAD", "/nope").status == 404
        assert client.request("HEAD", "/books/1").status == 404

    def test_content_length_matches_the_body_on_every_kind_of_response(self, client, create):
        create()
        responses = [
            client.get("/books"),
            client.get("/books/1"),
            client.get("/books/2"),
            client.post("/books", json={}),
            client.request("PATCH", "/books"),
            client.get("/nope"),
        ]
        for response in responses:
            assert int(response.headers["content-length"]) == len(response.body)

    def test_an_unexpected_failure_is_a_generic_json_500(
        self, client, repository, monkeypatch, caplog
    ):
        def explode(*args, **kwargs):
            raise RuntimeError("secret internal detail")

        monkeypatch.setattr(repository, "list_books", explode)
        with caplog.at_level(logging.ERROR):
            response = client.get("/books")

        assert response.status == 500
        assert response.headers["content-type"] == "application/json"
        assert response.json() == {"error": "Internal server error"}
        assert b"secret internal detail" not in response.body
        assert any(
            record.exc_info and "secret internal detail" in str(record.exc_info[1])
            for record in caplog.records
        )  # the real cause is logged, with a traceback

    def test_the_app_keeps_serving_after_a_failure(self, client, repository, monkeypatch):
        monkeypatch.setattr(repository, "list_books", lambda *a, **k: 1 / 0)
        assert client.get("/books").status == 500
        monkeypatch.undo()
        assert client.get("/books").status == 200
