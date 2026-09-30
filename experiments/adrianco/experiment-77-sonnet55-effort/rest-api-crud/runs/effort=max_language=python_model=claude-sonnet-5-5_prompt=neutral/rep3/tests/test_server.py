"""End-to-end tests over real HTTP sockets, and the command-line entry point."""

from __future__ import annotations

import http.client
import logging
import os
import re
import runpy
import socket
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from bookapi.server import ThreadingWSGIServer, build_parser, main

SRC_DIR = Path(__file__).resolve().parents[1] / "src"

DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-17271-9"}
EMMA = {"title": "Emma", "author": "Jane Austen", "year": 1815, "isbn": "978-0-14-143958-7"}


# --- the running service ----------------------------------------------------------


def test_book_lifecycle_over_http(live_server):
    """Create, read, list, filter, update and delete a book through the real server."""
    created = live_server.request("POST", "/books", payload=DUNE)
    assert created.status == 201
    book = created.json()
    assert book == {"id": 1, **DUNE}

    location = created.headers["location"]
    assert location == "/books/1"
    assert live_server.request("GET", location).json() == book

    live_server.request("POST", "/books", payload=EMMA)
    everything = live_server.request("GET", "/books").json()
    assert [b["title"] for b in everything] == ["Dune", "Emma"]
    by_author = live_server.request("GET", "/books?author=jane%20austen").json()
    assert [b["title"] for b in by_author] == ["Emma"]

    updated = live_server.request("PUT", location, payload={**DUNE, "title": "Dune (1st ed.)"})
    assert updated.status == 200
    assert updated.json()["title"] == "Dune (1st ed.)"
    assert live_server.request("GET", location).json()["title"] == "Dune (1st ed.)"

    deleted = live_server.request("DELETE", location)
    assert deleted.status == 204
    assert deleted.body == b""
    assert live_server.request("GET", location).status == 404
    assert [b["title"] for b in live_server.request("GET", "/books").json()] == ["Emma"]


def test_health_check_over_http(live_server):
    reply = live_server.request("GET", "/health")
    assert reply.status == 200
    assert reply.headers["content-type"] == "application/json; charset=utf-8"
    assert reply.json() == {"status": "ok"}

    head = live_server.request("HEAD", "/health")
    assert head.status == 200
    assert head.body == b""


def test_errors_are_json_over_http(live_server):
    invalid = live_server.request("POST", "/books", payload={"author": "Someone"})
    assert invalid.status == 400
    assert invalid.json()["details"] == {"title": "is required"}

    assert live_server.request("POST", "/books", raw=b"{oops").status == 400
    assert live_server.request("GET", "/books/999").json() == {"error": "Book 999 not found"}
    assert live_server.request("GET", "/nowhere").status == 404

    not_allowed = live_server.request("DELETE", "/books")
    assert not_allowed.status == 405
    assert not_allowed.headers["allow"] == "GET, HEAD, POST"


def test_non_ascii_text_survives_the_round_trip(live_server):
    book = {"title": "Cien años de soledad", "author": "Gabriel García Márquez"}
    created = live_server.request("POST", "/books", payload=book).json()
    fetched = live_server.request("GET", f"/books/{created['id']}").json()
    assert (fetched["title"], fetched["author"]) == (book["title"], book["author"])
    filtered = live_server.request("GET", "/books?author=GABRIEL%20GARC%C3%8DA%20M%C3%81RQUEZ").json()
    assert [b["id"] for b in filtered] == [created["id"]]


def test_data_survives_a_server_restart(start_server, tmp_path):
    database = tmp_path / "persistent.db"
    first = start_server(database)
    book = first.request("POST", "/books", payload=DUNE).json()
    first.stop()

    second = start_server(database)
    assert second.request("GET", f"/books/{book['id']}").json() == book
    assert second.request("POST", "/books", payload=EMMA).json()["id"] == book["id"] + 1


def test_concurrent_clients_are_served_correctly(live_server):
    def add(n: int) -> int:
        reply = live_server.request("POST", "/books", payload={"title": f"Book {n}", "author": "Many"})
        assert reply.status == 201
        return reply.json()["id"]

    with ThreadPoolExecutor(max_workers=16) as pool:
        ids = list(pool.map(add, range(64)))

    assert len(set(ids)) == 64
    assert len(live_server.request("GET", "/books?author=many").json()) == 64


# --- hostile or unlucky clients -----------------------------------------------------


def test_unescaped_utf8_in_the_url_is_understood(live_server):
    """What curl sends for ``curl 'http://.../books?author=Gabriel%20García%20Márquez'``."""
    live_server.request("POST", "/books", payload={"title": "Cien años de soledad", "author": "Gabriel García Márquez"})

    reply = live_server.exchange("GET /books?author=Gabriel%20García%20Márquez HTTP/1.0\r\n\r\n".encode("utf-8"))

    assert reply.status == 200
    assert [book["title"] for book in reply.json()] == ["Cien años de soledad"]


def test_absurd_content_length_is_413_not_a_crash(live_server):
    reply = live_server.exchange(b"POST /books HTTP/1.0\r\nContent-Length: " + b"9" * 4301 + b"\r\n\r\n{}")
    assert reply.status == 413
    assert live_server.request("GET", "/health").status == 200


def test_chunked_upload_is_refused_over_http(live_server):
    request = (
        b"POST /books HTTP/1.1\r\nHost: x\r\nTransfer-Encoding: chunked\r\nConnection: close\r\n\r\n"
        b'19\r\n{"title":"a","author":"b"}\r\n0\r\n\r\n'
    )
    assert live_server.exchange(request).status == 411


def test_a_client_that_stalls_mid_upload_gets_a_408(start_server):
    server = start_server(timeout=0.5)
    # Promises 100 bytes, sends 15, then goes quiet.
    reply = server.exchange(b'POST /books HTTP/1.0\r\nContent-Length: 100\r\n\r\n{"title": "Dun')

    assert reply.status == 408
    assert reply.json() == {"error": "Timed out waiting for the request body"}
    assert server.request("GET", "/health").status == 200  # the server carries on


def test_an_idle_connection_is_closed_without_a_traceback(start_server, capsys):
    server = start_server(timeout=0.5)

    assert server.send_raw(b"") == b""  # connects, says nothing, is hung up on

    assert server.request("GET", "/health").status == 200
    assert "Traceback" not in capsys.readouterr().err


def test_control_characters_in_the_request_line_are_escaped_in_the_access_log(live_server, caplog):
    caplog.set_level(logging.INFO, logger="bookapi.server.access")

    live_server.exchange(b"GET /x\x1b[31mRED\x07 HTTP/1.0\r\n\r\n")

    logged = [record.getMessage() for record in caplog.records if record.name == "bookapi.server.access"]
    assert logged, "the request was not logged"
    assert not any("\x1b" in line or "\x07" in line for line in logged)
    assert any("\\x1b[31mRED\\x07" in line for line in logged)


# --- command line -----------------------------------------------------------------


@pytest.fixture
def clean_environment(monkeypatch):
    for name in ("BOOKAPI_HOST", "BOOKAPI_PORT", "BOOKAPI_DB"):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_defaults_bind_to_localhost_only(clean_environment):
    args = build_parser().parse_args([])
    assert (args.host, args.port, args.db) == ("127.0.0.1", 8000, "books.db")


def test_environment_variables_supply_the_defaults(clean_environment):
    clean_environment.setenv("BOOKAPI_HOST", "0.0.0.0")
    clean_environment.setenv("BOOKAPI_PORT", "9100")
    clean_environment.setenv("BOOKAPI_DB", "/data/library.db")
    args = build_parser().parse_args([])
    assert (args.host, args.port, args.db) == ("0.0.0.0", 9100, "/data/library.db")


def test_command_line_beats_the_environment(clean_environment):
    clean_environment.setenv("BOOKAPI_PORT", "9100")
    assert build_parser().parse_args(["--port", "9200"]).port == 9200


def test_empty_environment_variables_fall_back_to_the_safe_defaults(clean_environment):
    # An empty host would otherwise mean "every interface", silently exposing the service.
    for name in ("BOOKAPI_HOST", "BOOKAPI_PORT", "BOOKAPI_DB"):
        clean_environment.setenv(name, "")
    args = build_parser().parse_args([])
    assert (args.host, args.port, args.db) == ("127.0.0.1", 8000, "books.db")


@pytest.mark.parametrize("flag", ["--host", "--db"])
@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_host_and_database_arguments_are_rejected(clean_environment, flag, blank, capsys):
    # "" would bind every interface (--host) or an SQLite temp database that vanishes (--db).
    with pytest.raises(SystemExit) as excinfo:
        build_parser().parse_args([flag, blank])
    assert excinfo.value.code == 2
    assert flag in capsys.readouterr().err


@pytest.mark.parametrize("port", ["abc", "-1", "65536"])
def test_invalid_ports_are_rejected(clean_environment, port, capsys):
    with pytest.raises(SystemExit) as excinfo:
        build_parser().parse_args(["--port", port])
    assert excinfo.value.code == 2
    assert "port" in capsys.readouterr().err


def press_ctrl_c(self, poll_interval=0.5):
    """Stands in for ``serve_forever``: the user hits Ctrl+C as soon as the server is up."""
    raise KeyboardInterrupt


@pytest.mark.usefixtures("loopback")
def test_main_creates_the_database_and_stops_cleanly_on_ctrl_c(clean_environment, tmp_path, caplog):
    clean_environment.setattr(ThreadingWSGIServer, "serve_forever", press_ctrl_c)
    caplog.set_level(logging.INFO)  # pytest's own handlers make main()'s basicConfig a no-op
    database = tmp_path / "data" / "books.db"

    assert main(["--port", "0", "--db", str(database)]) == 0

    assert database.exists()
    assert "Serving" in caplog.text
    assert "Shutting down" in caplog.text


@pytest.fixture(params=["directory", "not-sqlite", "parent-is-a-file"])
def unusable_database(request, tmp_path) -> str:
    if request.param == "directory":
        return str(tmp_path)
    if request.param == "not-sqlite":
        bogus = tmp_path / "bogus.db"
        bogus.write_bytes(b"this is not an SQLite database " * 300)
        return str(bogus)
    (tmp_path / "file").write_text("in the way")
    return str(tmp_path / "file" / "books.db")


def test_main_reports_an_unusable_database_without_a_traceback(clean_environment, unusable_database, caplog):
    assert main(["--port", "0", "--db", unusable_database]) == 1
    assert "Cannot open database" in caplog.text
    assert "Traceback" not in caplog.text


@pytest.mark.usefixtures("loopback")
@pytest.mark.skipif(sys.platform == "win32", reason="SO_REUSEADDR lets a second socket bind a busy port on Windows")
def test_main_exits_with_an_error_when_the_port_is_taken(clean_environment, caplog):
    clean_environment.setattr(ThreadingWSGIServer, "serve_forever", press_ctrl_c)  # never hang if binding succeeds
    with socket.socket() as blocker:
        blocker.bind(("127.0.0.1", 0))
        blocker.listen()
        port = blocker.getsockname()[1]
        assert main(["--port", str(port), "--db", ":memory:"]) == 1
    assert "Cannot listen" in caplog.text


@pytest.mark.usefixtures("loopback")
def test_module_entry_point_exits_with_the_status_of_main(clean_environment, tmp_path):
    clean_environment.setattr(ThreadingWSGIServer, "serve_forever", press_ctrl_c)
    clean_environment.setattr(sys, "argv", ["bookapi", "--port", "0", "--db", str(tmp_path / "books.db")])

    with pytest.raises(SystemExit) as excinfo:
        runpy.run_module("bookapi", run_name="__main__")

    assert excinfo.value.code == 0


def read_until_started(process: subprocess.Popen) -> str:
    """Everything the server logged to stderr up to and including its start-up (or failure) line."""
    seen = []
    for line in process.stderr:
        seen.append(line)
        if "Serving" in line or "Cannot listen" in line:
            break
    return "".join(seen)


@pytest.mark.usefixtures("loopback")
@pytest.mark.skipif(os.name != "posix", reason="uses POSIX process termination")
def test_python_dash_m_bookapi_starts_a_working_server(clean_environment, tmp_path):
    """The documented run command: ``PYTHONPATH=src python -m bookapi``."""
    process = subprocess.Popen(
        [sys.executable, "-m", "bookapi", "--port", "0", "--db", str(tmp_path / "books.db")],
        env={**os.environ, "PYTHONPATH": str(SRC_DIR)},
        stderr=subprocess.PIPE,
        text=True,
    )
    watchdog = threading.Timer(20, process.kill)  # never hang the suite if start-up goes wrong
    watchdog.start()
    try:
        output = read_until_started(process)
        match = re.search(r"http://127\.0\.0\.1:(\d+)", output)
        assert match, f"unexpected start-up output: {output!r}"

        connection = http.client.HTTPConnection("127.0.0.1", int(match.group(1)), timeout=10)
        try:
            connection.request("GET", "/health")
            response = connection.getresponse()
            assert (response.status, response.read()) == (200, b'{"status":"ok"}')
        finally:
            connection.close()
    finally:
        watchdog.cancel()
        process.kill()  # nothing to shut down gracefully: every write was already committed
        process.wait()
        process.stderr.close()
