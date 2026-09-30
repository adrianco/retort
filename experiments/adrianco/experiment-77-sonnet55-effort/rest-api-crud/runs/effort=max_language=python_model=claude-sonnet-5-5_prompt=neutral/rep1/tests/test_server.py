"""End-to-end tests against a real HTTP server on a loopback socket, plus the CLI."""

import http.client
import json
import logging
import os
import queue
import re
import runpy
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from bookapi import BookAPI, BookRepository, create_app
from bookapi import server as server_module
from bookapi.server import RequestHandler, main, make_book_server, parse_args

SRC = Path(__file__).resolve().parents[1] / "src"
DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}
POSIX_ONLY = pytest.mark.skipif(sys.platform == "win32", reason="relies on POSIX signals")


class Reply:
    def __init__(self, status, headers, body):
        self.status, self.headers, self.body = status, headers, body

    def json(self):
        return json.loads(self.body)


def http_request(host, port, method, path, body=None):
    conn = http.client.HTTPConnection(host, port, timeout=10)
    try:
        payload = None if body is None else json.dumps(body)
        headers = {} if body is None else {"Content-Type": "application/json"}
        conn.request(method, path, body=payload, headers=headers)
        response = conn.getresponse()
        return Reply(
            response.status, {k.lower(): v for k, v in response.getheaders()}, response.read()
        )
    finally:
        conn.close()


class LiveServer:
    """A real server on an ephemeral loopback port, serving from a background thread."""

    def __init__(self, database):
        self.repository = BookRepository(database)
        self.server = make_book_server(BookAPI(self.repository), "127.0.0.1", 0)
        self.host, self.port = self.server.server_address[:2]
        self._thread = threading.Thread(
            target=self.server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True
        )

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc_info):
        self.server.shutdown()
        self._thread.join(timeout=10)
        self.server.server_close()
        self.repository.close()

    def request(self, method, path, body=None):
        return http_request(self.host, self.port, method, path, body)

    def raw(self, data, timeout=10):
        """Send raw bytes and return everything the server writes before closing."""
        chunks = []
        with socket.create_connection((self.host, self.port), timeout=timeout) as sock:
            sock.sendall(data)
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
        return b"".join(chunks)


@pytest.fixture
def live(tmp_path):
    with LiveServer(tmp_path / "books.db") as server:
        yield server


class TestOverRealHttp:
    def test_full_book_lifecycle(self, live):
        created = live.request("POST", "/books", DUNE)
        assert created.status == 201
        assert created.headers["content-type"] == "application/json"
        book = created.json()
        location = created.headers["location"]
        assert location == f"/books/{book['id']}"
        assert book == {"id": book["id"], **DUNE}

        assert live.request("GET", location).json() == book
        assert live.request("GET", "/books").json() == [book]
        assert live.request("GET", "/books?author=frank%20herbert").json() == [book]
        assert live.request("GET", "/books?author=someone%20else").json() == []

        replacement = {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}
        updated = live.request("PUT", location, replacement)
        assert updated.status == 200
        assert updated.json() == {"id": book["id"], "isbn": None, **replacement}
        assert live.request("GET", location).json() == updated.json()

        deleted = live.request("DELETE", location)
        assert (deleted.status, deleted.body) == (204, b"")
        assert live.request("GET", location).status == 404
        assert live.request("GET", "/books").json() == []

    def test_health_check_and_head(self, live):
        get = live.request("GET", "/health")
        head = live.request("HEAD", "/health")

        assert (get.status, get.json()) == (200, {"status": "ok"})
        assert head.status == 200
        assert head.body == b""
        assert head.headers["content-length"] == str(len(get.body))

    def test_errors_are_json_end_to_end(self, live):
        invalid = live.request("POST", "/books", {"author": "Someone"})
        assert invalid.status == 400
        assert invalid.json()["details"] == {"title": "title is required"}

        missing = live.request("GET", "/books/999")
        assert (missing.status, missing.json()) == (404, {"error": "Book not found"})

        wrong_method = live.request("PATCH", "/books/1")
        assert wrong_method.status == 405
        assert wrong_method.headers["allow"] == "DELETE, GET, HEAD, OPTIONS, PUT"

        garbage = live.raw(b"POST /books HTTP/1.0\r\nContent-Length: 8\r\n\r\nnot json")
        assert garbage.startswith(b"HTTP/1.0 400")
        assert json.loads(garbage.partition(b"\r\n\r\n")[2]) == {
            "error": "Request body must be valid JSON"
        }

    @pytest.mark.parametrize(
        ("request_bytes", "status"),
        [
            (b"GARBAGE\r\n", 400),  # not a request line at all
            (b"GET / HTTP/9.9\r\n", 505),
            (b"GET /" + b"a" * 65532, 414),  # one byte over the 64 KiB request-line limit
        ],
    )
    def test_errors_raised_by_the_http_layer_are_json_too(self, live, request_bytes, status):
        # Each request is sent so that the server has consumed all of it when it rejects it:
        # closing a socket that still holds unread input resets the connection and can lose
        # the reply. A proper HTTP/1.0 status line is expected on every Python version, even
        # though the stdlib alone answers an unparseable request line without one on some.
        raw = live.raw(request_bytes)

        head, _, body = raw.partition(b"\r\n\r\n")
        assert head.startswith(f"HTTP/1.0 {status}".encode())
        assert b"Content-Type: application/json" in head
        assert "error" in json.loads(body)

    def test_head_requests_rejected_by_the_http_layer_get_no_body(self, live):
        # Exactly 101 headers, the number after which the server gives up (431).
        headers = b"".join(b"X-Header-%d: 1\r\n" % n for n in range(101))

        raw = live.raw(b"HEAD /health HTTP/1.0\r\n" + headers)

        head, _, body = raw.partition(b"\r\n\r\n")
        assert head.startswith(b"HTTP/1.0 431")
        assert b"Content-Length: " in head
        assert body == b""

    def test_control_characters_in_a_request_line_are_escaped_in_the_log(self, live, caplog):
        caplog.set_level(logging.INFO, logger="bookapi.server")

        live.raw(b"GET /\x1b[31mred\\ HTTP/1.0\r\n\r\n")  # an ESC and a backslash

        assert "\x1b" not in caplog.text  # the raw byte never reaches the log...
        assert "/\\x1b[31mred\\\\ HTTP/1.0" in caplog.text  # ...its escaped form does

    def test_concurrent_clients_are_all_served(self, live, run_concurrently):
        replies = []

        def worker(n):
            for i in range(5):
                replies.append(
                    live.request("POST", "/books", {"title": f"Book {n}-{i}", "author": "Someone"})
                )
                assert live.request("GET", "/books?author=someone").status == 200

        run_concurrently(worker, 20)

        assert {reply.status for reply in replies} == {201}
        assert len({reply.json()["id"] for reply in replies}) == 100
        assert len(live.request("GET", "/books").json()) == 100

    def test_unencoded_utf8_in_the_query_string_is_understood(self, live):
        live.request("POST", "/books", {"title": "Cien años de soledad", "author": "García"})

        # curl and friends do not percent-encode non-ASCII characters in the URL.
        raw = live.raw("GET /books?author=GARCÍA HTTP/1.0\r\n\r\n".encode())

        head, _, body = raw.partition(b"\r\n\r\n")
        assert head.startswith(b"HTTP/1.0 200")
        assert [book["title"] for book in json.loads(body)] == ["Cien años de soledad"]

    def test_a_client_that_stalls_mid_body_gets_a_408(self, live, monkeypatch):
        monkeypatch.setattr(RequestHandler, "timeout", 0.3)

        raw = live.raw(b'POST /books HTTP/1.0\r\nContent-Length: 50\r\n\r\n{"title"')

        assert raw.startswith(b"HTTP/1.0 408")
        assert live.request("GET", "/health").status == 200  # and the server carries on

    def test_an_idle_connection_is_dropped_quietly(self, live, monkeypatch, capsys):
        monkeypatch.setattr(RequestHandler, "timeout", 0.2)

        assert live.raw(b"") == b""

        assert live.request("GET", "/health").status == 200
        assert "Traceback" not in capsys.readouterr().err

    def test_data_survives_a_server_restart(self, tmp_path):
        database = tmp_path / "books.db"
        with LiveServer(database) as first:
            created = first.request("POST", "/books", DUNE).json()

        with LiveServer(database) as second:
            assert second.request("GET", f"/books/{created['id']}").json() == created
            assert second.request("POST", "/books", DUNE).json()["id"] > created["id"]


class TestCreateApp:
    def test_uses_the_given_database(self, tmp_path):
        app = create_app(tmp_path / "given.db")
        try:
            app.repository.ping()
        finally:
            app.repository.close()
        assert (tmp_path / "given.db").exists()

    def test_falls_back_to_the_environment_and_then_the_default(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("BOOKS_DB", raising=False)
        create_app().repository.close()
        assert (tmp_path / "books.db").exists()

        monkeypatch.setenv("BOOKS_DB", str(tmp_path / "from-env.db"))
        create_app().repository.close()
        assert (tmp_path / "from-env.db").exists()


class TestParseArgs:
    @pytest.fixture(autouse=True)
    def _clean_environment(self, monkeypatch):
        for name in ("BOOKS_HOST", "BOOKS_PORT", "BOOKS_DB"):
            monkeypatch.delenv(name, raising=False)

    def test_defaults_are_local_only(self):
        args = parse_args([])
        assert (args.host, args.port, args.db) == ("127.0.0.1", 8000, "books.db")

    def test_environment_variables_change_the_defaults(self, monkeypatch):
        monkeypatch.setenv("BOOKS_HOST", "0.0.0.0")
        monkeypatch.setenv("BOOKS_PORT", "9000")
        monkeypatch.setenv("BOOKS_DB", "/data/shelf.db")

        args = parse_args([])

        assert (args.host, args.port, args.db) == ("0.0.0.0", 9000, "/data/shelf.db")

    def test_flags_beat_the_environment(self, monkeypatch):
        monkeypatch.setenv("BOOKS_PORT", "9000")
        assert parse_args(["--port", "1234", "--host", "::1", "--db", "x.db"]).port == 1234

    @pytest.mark.parametrize("port", ["abc", "-1", "65536", "1.5", ""])
    def test_bad_ports_are_rejected(self, port, capsys):
        with pytest.raises(SystemExit) as excinfo:
            parse_args(["--port", port])
        assert excinfo.value.code == 2
        assert "port" in capsys.readouterr().err

    def test_a_bad_port_in_the_environment_is_rejected_too(self, monkeypatch, capsys):
        monkeypatch.setenv("BOOKS_PORT", "eighty")
        with pytest.raises(SystemExit):
            parse_args([])
        assert "invalid port" in capsys.readouterr().err


class TestMain:
    @pytest.mark.parametrize("kind", ["junk-file", "directory"])
    def test_an_unopenable_database_is_a_clean_error(self, tmp_path, capsys, kind):
        path = tmp_path / "shelf.db"
        if kind == "junk-file":
            path.write_bytes(b"this is not an sqlite database" * 20)
        else:
            path.mkdir()

        assert main(["--port", "0", "--db", str(path)]) == 1

        assert "cannot open database" in capsys.readouterr().err

    def test_a_port_that_is_taken_is_a_clean_error(self, tmp_path, capsys):
        with socket.socket() as blocker:
            blocker.bind(("127.0.0.1", 0))
            blocker.listen()
            port = blocker.getsockname()[1]

            assert main(["--port", str(port), "--db", str(tmp_path / "shelf.db")]) == 1

        assert f"cannot listen on 127.0.0.1:{port}" in capsys.readouterr().err

    def test_the_module_entry_point_exits_with_the_status_of_main(self, monkeypatch):
        monkeypatch.setattr(server_module, "main", lambda argv=None: 7)

        with pytest.raises(SystemExit) as excinfo:
            runpy.run_module("bookapi", run_name="__main__")

        assert excinfo.value.code == 7

    def test_sigterm_handling_is_skipped_outside_the_main_thread(self):
        # Signal handlers can only be installed from the main thread; embedding the server
        # in another thread must not blow up.
        outcome = {}

        def run():
            try:
                with server_module._sigterm_as_interrupt():
                    outcome["entered"] = True
            except BaseException as exc:  # pragma: no cover - only on failure
                outcome["error"] = exc

        thread = threading.Thread(target=run)
        thread.start()
        thread.join()

        assert outcome == {"entered": True}

    @POSIX_ONLY
    def test_sigterm_stops_the_server_cleanly(self, tmp_path, monkeypatch, caplog):
        caplog.set_level(logging.INFO, logger="bookapi.server")
        servers = []
        real_make = server_module.make_book_server

        def recording_make(*args, **kwargs):
            servers.append(real_make(*args, **kwargs))
            return servers[-1]

        monkeypatch.setattr(server_module, "make_book_server", recording_make)

        # Stand-in handler: if main() forgot to install its own, SIGTERM lands here instead
        # of killing the test run.
        stray_signals = []

        def sentinel(signum, frame):
            stray_signals.append(signum)

        previous = signal.signal(signal.SIGTERM, sentinel)
        outcome, main_returned = {}, threading.Event()

        def drive():
            try:
                deadline = time.monotonic() + 10
                while not servers:
                    assert time.monotonic() < deadline, "the server never came up"
                    time.sleep(0.01)
                host, port = servers[0].server_address[:2]
                outcome["health"] = http_request(host, port, "GET", "/health").json()
            except BaseException as exc:  # reported by the main thread below
                outcome["error"] = exc
            finally:
                os.kill(os.getpid(), signal.SIGTERM)
                if not main_returned.wait(10) and servers:
                    servers[0].shutdown()  # fail-safe: a regression must fail, not hang

        driver = threading.Thread(target=drive)
        driver.start()
        try:
            exit_code = main(["--port", "0", "--db", str(tmp_path / "shelf.db")])
        finally:
            main_returned.set()
            driver.join(20)
            handler_afterwards = signal.getsignal(signal.SIGTERM)
            signal.signal(signal.SIGTERM, previous)

        assert "error" not in outcome, outcome.get("error")
        assert outcome["health"] == {"status": "ok"}
        assert stray_signals == []  # main() handled SIGTERM itself...
        assert exit_code == 0
        assert handler_afterwards is sentinel  # ...and put the previous handler back
        assert "Shutting down" in caplog.text


@POSIX_ONLY
class TestCommandLine:
    @staticmethod
    def _environment():
        env = {k: v for k, v in os.environ.items() if not k.startswith("BOOKS_")}
        env["PYTHONPATH"] = str(SRC)
        return env

    def test_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "bookapi", "--help"],
            env=self._environment(),
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "--port" in result.stdout and "--db" in result.stdout

    def test_python_dash_m_bookapi_serves_requests_and_stops_on_sigterm(self, tmp_path):
        database = tmp_path / "cli.db"
        command = [sys.executable, "-m", "bookapi", "--port", "0", "--db", str(database)]
        with subprocess.Popen(
            command,
            env=self._environment(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        ) as proc:
            lines = queue.Queue()

            def pump():
                for line in proc.stderr:
                    lines.put(line)
                lines.put(None)

            pumper = threading.Thread(target=pump, daemon=True)
            pumper.start()
            try:
                port, deadline = None, time.monotonic() + 30
                while port is None:
                    line = lines.get(timeout=max(0.1, deadline - time.monotonic()))
                    assert line is not None, "the server exited before it started listening"
                    found = re.search(r"Serving on http://127\.0\.0\.1:(\d+)", line)
                    port = int(found.group(1)) if found else None

                created = http_request("127.0.0.1", port, "POST", "/books", DUNE)
                assert created.status == 201
                assert http_request("127.0.0.1", port, "GET", "/health").json() == {"status": "ok"}
            finally:
                proc.terminate()
                try:
                    returncode = proc.wait(timeout=15)
                except subprocess.TimeoutExpired:  # pragma: no cover - only on failure
                    proc.kill()
                    raise
                pumper.join(timeout=5)

        assert returncode == 0
        assert database.exists()
