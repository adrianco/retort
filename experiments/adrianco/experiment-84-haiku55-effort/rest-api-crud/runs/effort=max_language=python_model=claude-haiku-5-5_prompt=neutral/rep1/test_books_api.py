"""Tests for the book collection API.

Run from this directory with either:

    python -m unittest -v
    python -m pytest
"""

import concurrent.futures
import http.client
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import date
from typing import Any, NamedTuple

from server import MAX_BODY_BYTES, create_server
from store import BookStore
from validation import ValidationError, validate_book

HOBBIT = {"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937, "isbn": "9780547928227"}

# Ignore HTTP(S)_PROXY settings so requests to 127.0.0.1 go straight to the test server.
_DIRECT_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class Reply(NamedTuple):
    status: int
    headers: Any
    body: Any


def _json_or_none(data: bytes) -> Any:
    return json.loads(data) if data else None


class ValidationTests(unittest.TestCase):
    def test_create_requires_title_and_author(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_book({"year": 1999})
        self.assertEqual(ctx.exception.errors, {"title": "is required", "author": "is required"})

    def test_text_fields_are_trimmed_and_blank_values_rejected(self):
        self.assertEqual(
            validate_book({"title": "  1984 ", "author": " George Orwell "}),
            {"title": "1984", "author": "George Orwell", "year": None, "isbn": None},
        )
        with self.assertRaises(ValidationError) as ctx:
            validate_book({"title": "   ", "author": 42})
        self.assertEqual(ctx.exception.errors, {"title": "must not be empty", "author": "must be a string"})

    def test_title_length_is_capped(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_book({"title": "x" * 256, "author": "y"})
        self.assertIn("title", ctx.exception.errors)

    def test_year_must_be_an_integer_in_range(self):
        too_late = date.today().year + 2
        for bad in ("1999", 1999.0, True, 0, too_late):
            with self.subTest(year=bad), self.assertRaises(ValidationError) as ctx:
                validate_book({"title": "t", "author": "a", "year": bad})
            self.assertIn("year", ctx.exception.errors)
        self.assertEqual(validate_book({"title": "t", "author": "a", "year": 1937})["year"], 1937)

    def test_isbn_format_is_checked_but_check_digit_is_not(self):
        for good in ("0306406152", "030640615X", "978-0-306-40615-7", "978 0 306 40615 7"):
            with self.subTest(isbn=good):
                self.assertEqual(validate_book({"title": "t", "author": "a", "isbn": good})["isbn"], good)
        for bad in ("12345", "9780306406157X", "978-0-306-4061-5-x", 9780306406157):
            with self.subTest(isbn=bad), self.assertRaises(ValidationError) as ctx:
                validate_book({"title": "t", "author": "a", "isbn": bad})
            self.assertIn("isbn", ctx.exception.errors)

    def test_partial_update_validates_only_supplied_fields(self):
        self.assertEqual(validate_book({"year": 2001}, partial=True), {"year": 2001})
        self.assertEqual(validate_book({"isbn": None}, partial=True), {"isbn": None})
        with self.assertRaises(ValidationError) as ctx:
            validate_book({"title": None}, partial=True)
        self.assertEqual(ctx.exception.errors, {"title": "must be a string"})

    def test_partial_update_needs_at_least_one_known_field(self):
        for payload in ({}, {"id": 5}):
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                validate_book(payload, partial=True)

    def test_payload_must_be_a_json_object(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_book(["Dune", "Herbert"])
        self.assertIn("body", ctx.exception.errors)


class BookStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = BookStore()  # in-memory database
        self.addCleanup(self.store.close)

    def test_create_get_update_delete(self):
        book = self.store.create(**HOBBIT)
        self.assertEqual(self.store.get(book["id"]), book)
        self.assertEqual(self.store.update(book["id"], {"year": 1951}), {**book, "year": 1951})
        self.assertTrue(self.store.delete(book["id"]))
        self.assertIsNone(self.store.get(book["id"]))
        self.assertFalse(self.store.delete(book["id"]))
        self.assertIsNone(self.store.update(book["id"], {"year": 1}))

    def test_author_filter_is_case_insensitive_and_otherwise_exact(self):
        self.store.create(**HOBBIT)
        self.store.create(title="The Silmarillion", author="J.R.R. Tolkien", year=None, isbn=None)
        self.store.create(title="1984", author="George Orwell", year=1949, isbn=None)
        self.assertEqual(len(self.store.list_books(author="j.r.r. TOLKIEN")), 2)
        self.assertEqual(self.store.list_books(author="Tolkien"), [])
        self.assertEqual(len(self.store.list_books()), 3)

    def test_author_filter_folds_non_ascii_case(self):
        self.store.create(title="Nana", author="Émile Zola", year=1880, isbn=None)
        self.assertEqual(len(self.store.list_books(author="émile zola")), 1)

    def test_ids_are_not_reused_after_delete(self):
        first = self.store.create(**HOBBIT)
        self.store.delete(first["id"])
        second = self.store.create(**HOBBIT)
        self.assertGreater(second["id"], first["id"])

    def test_data_survives_reopening_the_database_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "books.db")
            first = BookStore(path)
            created = first.create(**HOBBIT)
            first.close()
            second = BookStore(path)
            try:
                self.assertEqual(second.get(created["id"]), created)
            finally:
                second.close()


class BookApiTests(unittest.TestCase):
    """Run the real HTTP server on an ephemeral port with a file-backed database."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.server = create_server(os.path.join(tmp.name, "books.db"), "127.0.0.1", 0)
        self.addCleanup(self.server.store.close)
        self.addCleanup(self.server.server_close)
        worker = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        worker.start()
        self.addCleanup(worker.join, 5)
        self.addCleanup(self.server.shutdown)
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def send(self, method, path, payload=None, *, raw=None, content_type="application/json"):
        body = raw
        headers = {}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
        if body is not None:
            headers["Content-Type"] = content_type
        request = urllib.request.Request(self.base_url + path, data=body, method=method, headers=headers)
        try:
            with _DIRECT_OPENER.open(request, timeout=5) as response:
                return Reply(response.status, response.headers, _json_or_none(response.read()))
        except urllib.error.HTTPError as error:
            with error:
                return Reply(error.code, error.headers, _json_or_none(error.read()))

    def create(self, payload):
        reply = self.send("POST", "/books", payload)
        self.assertEqual(reply.status, 201)
        return reply.body

    def test_health_reports_ok(self):
        reply = self.send("GET", "/health")
        self.assertEqual((reply.status, reply.body), (200, {"status": "ok"}))

    def test_create_returns_201_with_location_and_stored_book(self):
        reply = self.send("POST", "/books", HOBBIT)
        self.assertEqual(reply.status, 201)
        self.assertEqual(reply.headers["Location"], f"/books/{reply.body['id']}")
        self.assertEqual(reply.body, {"id": reply.body["id"], **HOBBIT})

    def test_optional_fields_can_be_omitted(self):
        book = self.create({"title": "Dune", "author": "Frank Herbert"})
        self.assertIsNone(book["year"])
        self.assertIsNone(book["isbn"])

    def test_create_reports_each_missing_required_field(self):
        reply = self.send("POST", "/books", {"year": 1999})
        self.assertEqual(reply.status, 400)
        self.assertEqual(reply.body["error"], "Validation failed")
        self.assertEqual(reply.body["details"], {"title": "is required", "author": "is required"})

    def test_create_rejects_bad_year_and_isbn(self):
        for field, bad in (("year", "1937"), ("year", 0), ("isbn", "12345")):
            with self.subTest(field=field, value=bad):
                reply = self.send("POST", "/books", {**HOBBIT, field: bad})
                self.assertEqual(reply.status, 400)
                self.assertIn(field, reply.body["details"])

    def test_malformed_json_is_400(self):
        reply = self.send("POST", "/books", raw=b'{"title": ')
        self.assertEqual(reply.status, 400)
        self.assertEqual(reply.body["error"], "Request body must be valid JSON")

    def test_non_json_content_type_is_415(self):
        reply = self.send(
            "POST", "/books", raw=b"title=Dune&author=Herbert", content_type="application/x-www-form-urlencoded"
        )
        self.assertEqual(reply.status, 415)

    def test_content_type_parameters_are_accepted(self):
        reply = self.send(
            "POST", "/books", raw=json.dumps(HOBBIT).encode(), content_type="application/json; charset=utf-8"
        )
        self.assertEqual(reply.status, 201)

    def test_concurrent_creates_all_persist_with_unique_ids(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            replies = list(
                pool.map(lambda n: self.send("POST", "/books", {"title": f"Book {n}", "author": "Load"}), range(40))
            )
        self.assertEqual({reply.status for reply in replies}, {201})
        self.assertEqual(len({reply.body["id"] for reply in replies}), 40)
        self.assertEqual(len(self.send("GET", "/books?author=load").body), 40)

    def test_oversized_body_is_413(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=5)
        self.addCleanup(conn.close)
        conn.putrequest("POST", "/books")
        conn.putheader("Content-Type", "application/json")
        conn.putheader("Content-Length", str(MAX_BODY_BYTES + 1))
        conn.endheaders()  # the server rejects on the header alone, so no body is sent
        response = conn.getresponse()
        self.assertEqual(response.status, 413)
        self.assertIn("error", json.loads(response.read()))

    def test_get_book_by_id_and_unknown_ids(self):
        book = self.create(HOBBIT)
        reply = self.send("GET", f"/books/{book['id']}")
        self.assertEqual((reply.status, reply.body), (200, book))
        self.assertEqual(self.send("GET", "/books/999999").status, 404)
        self.assertEqual(self.send("GET", "/books/not-a-number").status, 404)
        self.assertEqual(self.send("GET", "/books/99999999999999999999999").status, 404)

    def test_list_books_and_filter_by_author(self):
        self.create(HOBBIT)
        self.create({"title": "1984", "author": "George Orwell"})
        everything = self.send("GET", "/books")
        self.assertEqual(everything.status, 200)
        self.assertEqual([book["title"] for book in everything.body], ["The Hobbit", "1984"])
        filtered = self.send("GET", "/books?author=george%20orwell").body
        self.assertEqual([book["title"] for book in filtered], ["1984"])

    def test_put_updates_supplied_fields_and_clears_on_null(self):
        book = self.create(HOBBIT)
        reply = self.send("PUT", f"/books/{book['id']}", {"year": 1951, "isbn": None})
        self.assertEqual(reply.status, 200)
        self.assertEqual(reply.body, {**book, "year": 1951, "isbn": None})
        self.assertEqual(self.send("GET", f"/books/{book['id']}").body, reply.body)

    def test_put_rejects_invalid_changes_and_unknown_books(self):
        book = self.create(HOBBIT)
        self.assertEqual(self.send("PUT", f"/books/{book['id']}", {"title": ""}).status, 400)
        self.assertEqual(self.send("PUT", f"/books/{book['id']}", {}).status, 400)
        self.assertEqual(self.send("PUT", "/books/999999", {"title": "Missing"}).status, 404)

    def test_delete_removes_the_book(self):
        book = self.create(HOBBIT)
        reply = self.send("DELETE", f"/books/{book['id']}")
        self.assertEqual(reply.status, 204)
        self.assertIsNone(reply.body)
        self.assertEqual(self.send("GET", f"/books/{book['id']}").status, 404)
        self.assertEqual(self.send("DELETE", f"/books/{book['id']}").status, 404)

    def test_unknown_paths_and_unsupported_methods(self):
        self.assertEqual(self.send("GET", "/nope").status, 404)
        reply = self.send("POST", "/health")
        self.assertEqual((reply.status, reply.headers["Allow"]), (405, "GET"))
        book = self.create(HOBBIT)
        reply = self.send("PATCH", f"/books/{book['id']}", {"year": 1938})
        self.assertEqual((reply.status, reply.headers["Allow"]), (405, "DELETE, GET, PUT"))


if __name__ == "__main__":
    unittest.main()
