"""End-to-end tests over real HTTP: the threaded server and the CLI entry point."""

from __future__ import annotations

import json
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from books_api import BookRepository, BooksApp, create_app
from books_api.__main__ import parse_args
from books_api.server import make_server

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def http(method: str, url: str, payload=None) -> tuple[int, dict[str, str], object]:
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            status, headers, raw = response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as error:
        with error:
            status, headers, raw = error.code, dict(error.headers), error.read()
    return status, headers, json.loads(raw) if raw else None


@pytest.fixture
def base_url(tmp_path):
    repository = BookRepository(tmp_path / "server.db")
    server = make_server("127.0.0.1", 0, BooksApp(repository))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
    repository.close()


def test_full_crud_lifecycle_over_http(base_url):
    assert http("GET", f"{base_url}/health")[0] == 200

    status, headers, created = http(
        "POST", f"{base_url}/books", {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
    )
    assert status == 201
    assert headers["Content-Type"] == "application/json"
    assert headers["Location"] == f"/books/{created['id']}"
    book_url = f"{base_url}/books/{created['id']}"

    status, _, fetched = http("GET", book_url)
    assert (status, fetched) == (200, created)
    assert http("GET", f"{base_url}/books?author=herbert")[2] == [created]

    status, _, updated = http("PUT", book_url, {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969})
    assert status == 200
    assert updated == {"id": created["id"], "title": "Dune Messiah", "author": "Frank Herbert", "year": 1969, "isbn": None}

    status, _, body = http("DELETE", book_url)
    assert (status, body) == (204, None)
    assert http("GET", book_url)[0] == 404
    assert http("GET", f"{base_url}/books")[2] == []


def test_validation_error_over_http(base_url):
    status, headers, body = http("POST", f"{base_url}/books", {"year": 1965})
    assert status == 400
    assert headers["Content-Type"] == "application/json"
    assert body["details"] == {"title": "title is required", "author": "author is required"}


def test_concurrent_requests(base_url):
    def create(n):
        return http("POST", f"{base_url}/books", {"title": f"Book {n}", "author": "Many Hands"})[0]

    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(create, range(40)))

    assert statuses == [201] * 40
    books = http("GET", f"{base_url}/books?author=many")[2]
    assert sorted(book["title"] for book in books) == sorted(f"Book {n}" for n in range(40))


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.mark.skipif(sys.platform == "win32", reason="uses POSIX signals to stop the server")
@pytest.mark.parametrize("stop_signal", [signal.SIGINT, signal.SIGTERM], ids=["SIGINT", "SIGTERM"])
def test_cli_serves_requests_and_shuts_down_cleanly(tmp_path, stop_signal):
    port = _free_port()
    db_path = tmp_path / "cli.db"
    log_path = tmp_path / "server.log"
    base_url = f"http://127.0.0.1:{port}"

    with log_path.open("w") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "books_api", "--port", str(port), "--db", str(db_path)],
            cwd=PROJECT_ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 15
            while True:
                try:
                    if http("GET", f"{base_url}/health")[0] == 200:
                        break
                except OSError:
                    pass
                assert process.poll() is None, log_path.read_text()
                assert time.monotonic() < deadline, "server did not start:\n" + log_path.read_text()
                time.sleep(0.1)

            assert http("POST", f"{base_url}/books", {"title": "Dune", "author": "Frank Herbert"})[0] == 201
        finally:
            process.send_signal(stop_signal)
            try:
                exit_code = process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                raise

    log_text = log_path.read_text()
    assert exit_code == 0, log_text
    assert "Serving on" in log_text
    assert "Shutting down" in log_text
    repository = BookRepository(db_path)
    try:
        assert [book.title for book in repository.list_books()] == ["Dune"]
    finally:
        repository.close()


def test_cli_options_default_to_environment_variables(monkeypatch):
    monkeypatch.setenv("BOOKS_API_HOST", "0.0.0.0")
    monkeypatch.setenv("BOOKS_API_PORT", "9090")
    monkeypatch.setenv("BOOKS_API_DB", "/data/books.db")
    args = parse_args([])
    assert (args.host, args.port, args.db) == ("0.0.0.0", 9090, "/data/books.db")

    args = parse_args(["--host", "localhost", "--port", "0", "--db", ":memory:"])
    assert (args.host, args.port, args.db) == ("localhost", 0, ":memory:")


def test_create_app_uses_books_api_db_environment_variable(tmp_path, monkeypatch):
    db_path = tmp_path / "env.db"
    monkeypatch.setenv("BOOKS_API_DB", str(db_path))
    app = create_app()
    try:
        assert app.repository.ping()
        assert db_path.exists()
    finally:
        app.repository.close()
