"""End-to-end tests over real sockets, and the command-line entry point.

Every server here listens on an ephemeral port (port 0), so tests never collide
with each other or with anything else running on the machine.
"""

from __future__ import annotations

import http.client
import io
import json
import logging
import os
import queue
import re
import runpy
import socket
import sqlite3
import subprocess
import sys
import threading
import time
from contextlib import closing
from http import HTTPStatus
from pathlib import Path
from typing import Any

import pytest
from support import ApiResponse, book_payload, wait_for

from bookapi.app import create_app
from bookapi.server import (
    RequestHandler,
    ThreadingWSGIServer,
    build_parser,
    create_server,
    main,
)

SRC_DIR = Path(__file__).resolve().parent.parent / "src"


def call(address: tuple[str, int], method: str, path: str, body: Any = None) -> ApiResponse:
    """Make one real HTTP request and return the response."""
    connection = http.client.HTTPConnection(*address, timeout=5)
    try:
        payload = None if body is None else json.dumps(body)
        connection.request(method, path, body=payload, headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        headers = {name.lower(): value for name, value in response.getheaders()}
        return ApiResponse(response.status, headers, response.read())
    finally:
        connection.close()


def raw_exchange(address: tuple[str, int], request: bytes) -> bytes:
    """Send raw bytes and return everything the server answers until it closes."""
    with socket.create_connection(address, timeout=5) as sock:
        sock.sendall(request)
        received = b""
        while chunk := sock.recv(4096):
            received += chunk
    return received


def raw_request(address: tuple[str, int], request: bytes) -> tuple[bytes, bytes]:
    """Send raw bytes; return (status line and headers, body) of the answer."""
    head, _, body = raw_exchange(address, request).partition(b"\r\n\r\n")
    return head, body


def raw_get(address: tuple[str, int], target: str) -> tuple[bytes, bytes]:
    """GET with the target exactly as typed: raw UTF-8, not percent-encoded, like curl."""
    request = f"GET {target} HTTP/1.1\r\nHost: test\r\nConnection: close\r\n\r\n"
    return raw_request(address, request.encode("utf-8"))


def status_of(head: bytes) -> int:
    return int(head.split(b"\r\n")[0].split()[1])


@pytest.fixture
def live(tmp_path):
    """A running server on a free port, backed by a SQLite file; yields (host, port)."""
    app = create_app(tmp_path / "live.db")
    server = create_server(app, "127.0.0.1", 0)
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True
    )
    thread.start()
    try:
        yield server.server_address[:2]
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
        app.repository.close()


class TestOverRealSockets:
    def test_the_whole_api_works_over_http(self, live):
        health = call(live, "GET", "/health")
        assert (health.status, health.json()) == (200, {"status": "ok"})
        assert health.headers["content-type"] == "application/json"

        created = call(live, "POST", "/books", book_payload())
        assert created.status == 201
        assert created.headers["location"] == "/books/1"
        book = created.json()
        assert book == {"id": 1, **book_payload()}

        assert call(live, "GET", "/books").json() == [book]
        assert call(live, "GET", "/books?author=andrew+hunt").json() == [book]
        assert call(live, "GET", "/books?author=nobody").json() == []
        assert call(live, "GET", "/books/1").json() == book

        update = book_payload(title="Second Edition", year=2019)
        updated = call(live, "PUT", "/books/1", update)
        assert (updated.status, updated.json()) == (200, {"id": 1, **update})

        deleted = call(live, "DELETE", "/books/1")
        assert (deleted.status, deleted.body) == (204, b"")
        assert call(live, "GET", "/books/1").status == 404

    def test_errors_reach_the_client_as_json(self, live):
        invalid = call(live, "POST", "/books", {"title": "No author"})
        assert invalid.status == 400
        assert invalid.json()["details"] == {"author": "author is required"}

        missing = call(live, "GET", "/books/99")
        assert (missing.status, missing.json()) == (404, {"error": "Book not found"})

        not_json = call(live, "POST", "/books", None)
        assert not_json.status == 400

    def test_head_gets_headers_but_no_body(self, live):
        get = call(live, "GET", "/health")
        head = call(live, "HEAD", "/health")
        assert head.status == 200
        assert head.body == b""
        assert head.headers["content-length"] == str(len(get.body))

    def test_books_are_stored_in_the_sqlite_file(self, live, tmp_path):
        call(live, "POST", "/books", book_payload())
        with closing(sqlite3.connect(tmp_path / "live.db")) as database:
            rows = database.execute("SELECT id, title, author, year, isbn FROM books").fetchall()
        assert rows == [(1, "The Pragmatic Programmer", "Andrew Hunt", 1999, "978-0201616224")]

    # curl sends non-ASCII bytes in a URL exactly as typed. Several of these letters
    # contain a byte (0xA0 or 0x85) that http.server would mistake for whitespace and
    # cut the URL at: "à" is C3 A0, "Å" is C3 85, "Š" is C5 A0, "х" is D1 85.
    @pytest.mark.parametrize(
        "author", ["García", "Alà", "Åke", "Šimek", "Чехов", "夏目漱石"], ids=ascii
    )
    def test_unencoded_utf8_in_the_query_string_is_understood(self, live, author):
        call(live, "POST", "/books", book_payload(author=author))
        call(live, "POST", "/books", book_payload(author="Other"))
        head, body = raw_get(live, f"/books?author={author}")
        assert status_of(head) == 200
        assert [book["author"] for book in json.loads(body)] == [author]

    @pytest.mark.parametrize("target", ["/books/à", "/à/х", "/books?author=à&x=х"], ids=ascii)
    def test_unencoded_utf8_elsewhere_in_the_url_never_breaks_the_request(self, live, target):
        head, body = raw_get(live, target)
        assert b"application/json" in head.lower()
        assert status_of(head) in (200, 404)
        json.loads(body)  # a JSON body, not the standard library's HTML error page

    def test_an_oversized_declared_length_is_refused_before_any_body_arrives(self, live):
        head, body = raw_request(
            live,
            b"POST /books HTTP/1.1\r\nHost: t\r\nContent-Length: 100000000\r\n"
            b"Connection: close\r\n\r\n",
        )
        assert status_of(head) == 413
        assert "error" in json.loads(body)

    def test_a_chunked_request_body_is_refused_with_411(self, live):
        head, body = raw_request(
            live,
            b"POST /books HTTP/1.1\r\nHost: t\r\nTransfer-Encoding: chunked\r\n"
            b"Connection: close\r\n\r\n5\r\nhello\r\n0\r\n\r\n",
        )
        assert status_of(head) == 411
        assert "Content-Length" in json.loads(body)["error"]

    def test_many_clients_at_once_are_all_served(self, live):
        responses: list[ApiResponse] = []

        def client(number: int) -> None:
            for i in range(5):
                responses.append(call(live, "POST", "/books", book_payload(title=f"{number}-{i}")))

        threads = [threading.Thread(target=client, args=(n,)) for n in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert [r.status for r in responses] == [201] * 40
        assert sorted(r.json()["id"] for r in responses) == list(range(1, 41))
        assert len(call(live, "GET", "/books").json()) == 40


class TestAccessLog:
    def test_requests_are_logged_through_the_logging_module(self, live, caplog):
        with caplog.at_level(logging.INFO, logger="bookapi.access"):
            call(live, "GET", "/health")
            assert wait_for(lambda: '"GET /health HTTP/1.1" 200' in caplog.text)

    @pytest.mark.parametrize(
        ("char", "escaped"), [("\x1b", "\\x1b"), ("\x7f", "\\x7f"), ("\x00", "\\x00")], ids=ascii
    )
    def test_control_characters_in_a_request_are_escaped(self, live, caplog, char, escaped):
        request = f"GET /evil{char}tail HTTP/1.1\r\nHost: t\r\nConnection: close\r\n\r\n"
        with caplog.at_level(logging.INFO, logger="bookapi.access"):
            raw_exchange(live, request.encode())
            assert wait_for(lambda: "/evil" in caplog.text)
        assert char not in caplog.text
        assert f"/evil{escaped}tail" in caplog.text

    def test_c1_control_characters_are_escaped_too(self, caplog):
        # Not reachable through a request line (non-ASCII bytes are percent-encoded
        # first) but log messages have other sources, so the whole C1 range is covered.
        handler = object.__new__(RequestHandler)
        handler.client_address = ("203.0.113.9", 4242)
        with caplog.at_level(logging.INFO, logger="bookapi.access"):
            handler.log_message("%s", "a\x9bb\x85c\x80d\x9fe")
        assert "a\\x9bb\\x85c\\x80d\\x9fe" in caplog.text
        assert not any(char in caplog.text for char in "\x9b\x85\x80\x9f")


class TestProtocolErrors:
    """Requests broken beyond what the app ever sees still get JSON answers."""

    @pytest.mark.parametrize(
        ("request_line", "status"),
        [
            (b"GET /health HTTP/1.1 EXTRA", 400),
            (b"GET", 400),
            (b"GET /health HTTP/9.9", 505),
        ],
        ids=lambda value: repr(value)[:24],
    )
    def test_a_malformed_request_line_gets_a_json_error(self, live, request_line, status):
        head, body = raw_request(live, request_line + b"\r\nHost: t\r\nConnection: close\r\n\r\n")
        assert status_of(head) == status
        assert b"content-type: application/json" in head.lower()
        assert "error" in json.loads(body)

    @pytest.fixture
    def handler(self):
        handler = object.__new__(RequestHandler)  # the output can be checked without a socket
        handler.wfile = io.BytesIO()
        handler.client_address = ("127.0.0.1", 50000)
        handler.request_version = "HTTP/1.1"
        handler.requestline = "GET / HTTP/1.1"
        handler.command = "GET"
        return handler

    @staticmethod
    def answer(handler):
        head, _, body = handler.wfile.getvalue().partition(b"\r\n\r\n")
        headers = dict(line.split(b": ", 1) for line in head.split(b"\r\n")[1:])
        return head.split(b"\r\n")[0], headers, body

    def test_the_error_is_json_with_the_standard_reason_phrase(self, handler):
        handler.send_error(414)
        status_line, headers, body = self.answer(handler)
        assert status_line.split()[1] == b"414"
        assert headers[b"Content-Type"] == b"application/json"
        assert headers[b"Connection"] == b"close"
        assert int(headers[b"Content-Length"]) == len(body)
        assert json.loads(body) == {"error": HTTPStatus(414).phrase}

    def test_a_message_is_json_escaped_and_kept_out_of_the_status_line(self, handler):
        message = 'Bad "syntax"\r\nInjected: header'
        handler.send_error(400, message)
        status_line, headers, body = self.answer(handler)
        assert json.loads(body) == {"error": message}
        assert b"Injected" not in status_line
        assert b"Injected" not in b"".join(headers)

    @pytest.mark.parametrize("version", ["HTTP/0.9", "", "HTTP/1.1"])
    def test_a_status_line_is_sent_whatever_version_the_request_claimed(self, handler, version):
        # Older Pythons leave the version at HTTP/0.9 when the request line is unparseable,
        # which would make the standard library send a bare body with no status line.
        handler.request_version = version
        handler.send_error(400, "nope")
        status_line, headers, body = self.answer(handler)
        assert status_line.startswith(b"HTTP/")
        assert status_line.split()[1] == b"400"
        assert json.loads(body) == {"error": "nope"}

    def test_an_unknown_status_code_still_produces_a_response(self, handler):
        handler.send_error(599)
        status_line, _, body = self.answer(handler)
        assert status_line.split()[1] == b"599"
        assert json.loads(body) == {"error": "Error"}

    def test_a_head_request_gets_the_headers_only(self, handler):
        handler.command = "HEAD"
        handler.send_error(400, "nope")
        _, headers, body = self.answer(handler)
        assert body == b""
        assert int(headers[b"Content-Length"]) > 0


class TestStalledAndIdleClients:
    @pytest.fixture(autouse=True)
    def short_timeout(self, monkeypatch):
        # Short enough to keep the tests quick, long enough that a heavily loaded machine
        # still delivers the client's first bytes before the server gives up.
        monkeypatch.setattr(RequestHandler, "timeout", 0.5)

    def test_a_client_that_never_sends_a_request_is_dropped(self, live):
        with socket.create_connection(live, timeout=5) as sock:
            assert sock.recv(4096) == b""  # the server gave up and closed the connection

    def test_a_body_that_stalls_half_way_is_answered_with_408(self, live):
        head, body = raw_request(  # the client stays connected but goes silent
            live,
            b"POST /books HTTP/1.1\r\nHost: t\r\nContent-Length: 100\r\n"
            b'Connection: close\r\n\r\n{"title"',  # 8 of the promised 100 bytes
        )
        assert status_of(head) == 408
        assert "error" in json.loads(body)

    def test_the_server_keeps_working_afterwards(self, live):
        with socket.create_connection(live, timeout=5) as sock:
            assert sock.recv(4096) == b""
        assert call(live, "GET", "/health").status == 200


def test_a_stalled_client_is_given_up_on_after_a_finite_time_by_default():
    # The tests above shorten the timeout; this pins the value real servers run with.
    assert RequestHandler.timeout is not None
    assert 0 < RequestHandler.timeout <= 120


def test_shutting_down_does_not_wait_for_idle_clients(tmp_path):
    app = create_app(tmp_path / "s.db")
    server = create_server(app, "127.0.0.1", 0)
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True
    )
    thread.start()
    address = server.server_address[:2]
    try:
        with socket.create_connection(address, timeout=5):  # connects, then just sits there
            assert call(address, "GET", "/health").status == 200  # so it has been accepted
            started = time.monotonic()
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
            assert time.monotonic() - started < 5  # not the 30 s the idle handler could take
    finally:
        app.repository.close()


class TestConnectionErrors:
    """``handle_error`` decides what reaches the log when a connection goes wrong."""

    @pytest.fixture
    def server(self):
        return object.__new__(ThreadingWSGIServer)  # handle_error needs no bound socket

    @pytest.mark.parametrize(
        "error", [ConnectionResetError(), BrokenPipeError(), socket.timeout("timed out")], ids=repr
    )
    def test_hangups_and_timeouts_are_routine(self, server, caplog, error):
        with caplog.at_level(logging.DEBUG, logger="bookapi.server"):
            try:
                raise error
            except OSError:
                server.handle_error(None, ("203.0.113.5", 999))
        assert [r.levelno for r in caplog.records] == [logging.DEBUG]

    def test_anything_else_is_an_error_with_a_traceback(self, server, caplog):
        with caplog.at_level(logging.DEBUG, logger="bookapi.server"):
            try:
                raise RuntimeError("boom")
            except RuntimeError:
                server.handle_error(None, ("203.0.113.5", 999))
        (record,) = caplog.records
        assert record.levelno == logging.ERROR
        assert "203.0.113.5" in record.getMessage()
        assert record.exc_info is not None
        assert "boom" in str(record.exc_info[1])


def test_create_server_binds_a_threaded_server_on_the_requested_port(tmp_path):
    app = create_app(tmp_path / "s.db")
    server = create_server(app, "127.0.0.1", 0)
    try:
        assert isinstance(server, ThreadingWSGIServer)
        assert server.server_address[0] == "127.0.0.1"
        assert server.server_address[1] != 0  # the OS picked a real port
    finally:
        server.server_close()
        app.repository.close()


class TestCommandLine:
    @pytest.fixture(autouse=True)
    def clean_environment(self, monkeypatch):
        for name in ("BOOKS_HOST", "BOOKS_PORT", "BOOKS_DB"):
            monkeypatch.delenv(name, raising=False)

    def test_defaults(self):
        args = build_parser().parse_args([])
        assert (args.host, args.port, args.db) == ("127.0.0.1", 8000, "books.db")

    def test_environment_variables_override_the_defaults(self, monkeypatch):
        monkeypatch.setenv("BOOKS_HOST", "0.0.0.0")
        monkeypatch.setenv("BOOKS_PORT", "9001")
        monkeypatch.setenv("BOOKS_DB", "/data/library.db")
        args = build_parser().parse_args([])
        assert (args.host, args.port, args.db) == ("0.0.0.0", 9001, "/data/library.db")

    def test_environment_variables_that_are_empty_count_as_unset(self, monkeypatch):
        for name in ("BOOKS_HOST", "BOOKS_PORT", "BOOKS_DB"):
            monkeypatch.setenv(name, "")
        args = build_parser().parse_args([])
        assert (args.host, args.port, args.db) == ("127.0.0.1", 8000, "books.db")

    @pytest.mark.parametrize("value", ["", "   "], ids=repr)
    def test_a_blank_database_path_is_rejected(self, value, capsys):
        # SQLite would otherwise open a temporary database that is lost on exit.
        with pytest.raises(SystemExit) as excinfo:
            build_parser().parse_args(["--db", value])
        assert excinfo.value.code == 2
        assert "must not be empty" in capsys.readouterr().err

    def test_a_blank_database_path_in_the_environment_is_rejected(self, monkeypatch, capsys):
        monkeypatch.setenv("BOOKS_DB", "   ")
        with pytest.raises(SystemExit):
            build_parser().parse_args([])
        assert "must not be empty" in capsys.readouterr().err

    def test_an_in_memory_database_can_be_asked_for_explicitly(self):
        assert build_parser().parse_args(["--db", ":memory:"]).db == ":memory:"

    def test_flags_override_the_environment(self, monkeypatch):
        monkeypatch.setenv("BOOKS_PORT", "9001")
        monkeypatch.setenv("BOOKS_DB", "from-env.db")
        args = build_parser().parse_args(["--port", "9002", "--db", "from-flag.db"])
        assert (args.port, args.db) == (9002, "from-flag.db")

    @pytest.mark.parametrize("port", ["abc", "-1", "65536", "80.5", ""])
    def test_an_invalid_port_is_rejected(self, port, capsys):
        with pytest.raises(SystemExit) as excinfo:
            build_parser().parse_args(["--port", port])
        assert excinfo.value.code == 2
        assert "port" in capsys.readouterr().err

    def test_an_invalid_port_in_the_environment_is_rejected(self, monkeypatch, capsys):
        monkeypatch.setenv("BOOKS_PORT", "not-a-port")
        with pytest.raises(SystemExit):
            build_parser().parse_args([])
        assert "not-a-port" in capsys.readouterr().err

    def test_help_mentions_every_option_and_variable(self):
        text = build_parser().format_help()
        for expected in ("--host", "--port", "--db", "BOOKS_HOST", "BOOKS_PORT", "BOOKS_DB"):
            assert expected in text

    def test_main_serves_until_interrupted_then_cleans_up(self, tmp_path, monkeypatch, caplog):
        served: list[tuple] = []

        def interrupted(self, poll_interval=0.5):
            served.append(self.server_address)
            raise KeyboardInterrupt

        monkeypatch.setattr(ThreadingWSGIServer, "serve_forever", interrupted)
        database = tmp_path / "cli.db"
        with caplog.at_level(logging.INFO):
            status = main(["--host", "127.0.0.1", "--port", "0", "--db", str(database)])

        assert status == 0
        assert len(served) == 1
        assert database.exists()  # created on start-up
        assert f"Serving on http://127.0.0.1:{served[0][1]}" in caplog.text
        assert "Shutting down" in caplog.text

    def test_main_reports_a_database_it_cannot_open(self, tmp_path, caplog):
        unreachable = tmp_path / "no" / "such" / "directory" / "books.db"
        assert main(["--port", "0", "--db", str(unreachable)]) == 1
        assert "Cannot open database" in caplog.text

    def test_main_reports_a_port_that_is_already_taken(self, tmp_path, caplog):
        with socket.socket() as occupant:
            occupant.bind(("127.0.0.1", 0))
            occupant.listen()
            port = occupant.getsockname()[1]
            status = main(["--port", str(port), "--db", str(tmp_path / "books.db")])
        assert status == 1
        assert "Cannot listen on" in caplog.text

    def test_the_package_is_runnable_with_python_dash_m(self, monkeypatch):
        monkeypatch.setattr("bookapi.server.main", lambda argv=None: 7)
        with pytest.raises(SystemExit) as excinfo:
            runpy.run_module("bookapi", run_name="__main__")
        assert excinfo.value.code == 7

    def test_importing_the_main_module_does_not_start_a_server(self, monkeypatch):
        monkeypatch.setattr(
            "bookapi.server.main", lambda argv=None: pytest.fail("main() ran on import")
        )
        runpy.run_module("bookapi.__main__", run_name="imported_not_run")


def _wait_for_listening_address(process: subprocess.Popen, timeout: float = 20.0):
    """Read the child's log until it announces where it listens."""
    lines: queue.Queue[str] = queue.Queue()

    def pump() -> None:
        for line in process.stderr:
            lines.put(line)

    threading.Thread(target=pump, daemon=True).start()

    seen: list[str] = []
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            line = lines.get(timeout=0.2)
        except queue.Empty:
            if process.poll() is not None:
                break
            continue
        seen.append(line)
        match = re.search(r"Serving on http://([\d.]+):(\d+)", line)
        if match:
            return match.group(1), int(match.group(2))
    raise AssertionError("the server never announced its address; output was:\n" + "".join(seen))


def test_python_dash_m_bookapi_starts_a_working_server(tmp_path):
    """The exact command from the README, in a real subprocess."""
    env = {name: value for name, value in os.environ.items() if not name.startswith("BOOKS_")}
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(SRC_DIR), env.get("PYTHONPATH")]))
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "bookapi",
            *("--host", "127.0.0.1", "--port", "0", "--db", str(tmp_path / "e2e.db")),
        ],
        env=env,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        address = _wait_for_listening_address(process)
        assert call(address, "GET", "/health").json() == {"status": "ok"}
        created = call(address, "POST", "/books", book_payload())
        assert created.status == 201
        assert call(address, "GET", f"/books/{created.json()['id']}").json() == created.json()
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover - only if terminate() is ignored
            process.kill()
            process.wait()
        process.stderr.close()
    assert (tmp_path / "e2e.db").exists()
