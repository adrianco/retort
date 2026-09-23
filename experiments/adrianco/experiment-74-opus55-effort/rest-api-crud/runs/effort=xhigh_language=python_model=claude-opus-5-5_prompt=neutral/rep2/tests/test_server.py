"""Integration tests over real HTTP: the http.server transport and the CLI entry point."""

import http.client
import json
import re
import signal
import socket
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from books_api import create_server
from books_api.server import MAX_BODY_BYTES, BooksRequestHandler

from .samples import HUXLEY, ORWELL

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def server_address(app):
    server = create_server(app, "127.0.0.1", 0)
    # A short poll interval keeps shutdown() (and so each test teardown) fast.
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    yield server.server_address[:2]
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


@pytest.fixture
def conn(server_address):
    connection = http.client.HTTPConnection(*server_address, timeout=5)
    yield connection
    connection.close()


def send(conn, method, path, payload=None, *, body=None, headers=None):
    headers = dict(headers or {})
    if payload is not None:
        body = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    conn.request(method, path, body=body, headers=headers)
    response = conn.getresponse()
    raw = response.read()
    return response, (json.loads(raw) if raw else None)


def test_crud_round_trip_over_http(conn):
    response, created = send(conn, "POST", "/books", ORWELL)
    assert response.status == 201
    assert response.getheader("Content-Type") == "application/json"
    assert response.getheader("Location") == f"/books/{created['id']}"
    assert created == {"id": created["id"], **ORWELL}

    _, huxley = send(conn, "POST", "/books", HUXLEY)

    response, books = send(conn, "GET", "/books")
    assert response.status == 200
    assert books == [created, huxley]

    response, books = send(conn, "GET", "/books?author=orwell")
    assert response.status == 200
    assert books == [created]

    response, book = send(conn, "GET", f"/books/{created['id']}")
    assert (response.status, book) == (200, created)

    response, book = send(conn, "PUT", f"/books/{created['id']}", {"title": "Nineteen Eighty-Four"})
    assert response.status == 200
    assert book == {**created, "title": "Nineteen Eighty-Four"}

    response, body = send(conn, "DELETE", f"/books/{created['id']}")
    assert (response.status, body) == (204, None)

    response, body = send(conn, "GET", f"/books/{created['id']}")
    assert (response.status, body) == (404, {"error": "Book not found"})


def test_health_over_http(conn):
    response, body = send(conn, "GET", "/health")
    assert response.status == 200
    assert body["status"] == "ok"


def test_validation_error_over_http(conn):
    response, body = send(conn, "POST", "/books", {"author": "George Orwell"})
    assert response.status == 400
    assert response.getheader("Content-Type") == "application/json"
    assert body == {"error": "Validation failed", "details": {"title": "title is required"}}


def test_invalid_json_over_http(conn):
    response, body = send(conn, "POST", "/books", body=b"{oops", headers={"Content-Type": "application/json"})
    assert response.status == 400
    assert body == {"error": "Request body is not valid JSON"}


def test_connection_is_reused_across_requests(conn):
    # With HTTP/1.1 keep-alive, bad framing (e.g. a body on a 204) would break the next request.
    _, book = send(conn, "POST", "/books", ORWELL)
    sock = conn.sock
    assert send(conn, "DELETE", f"/books/{book['id']}")[0].status == 204
    assert send(conn, "GET", f"/books/{book['id']}")[0].status == 404
    assert send(conn, "POST", "/books", {"title": ""})[0].status == 400
    assert send(conn, "GET", "/books")[1] == []
    assert conn.sock is sock


def test_head_returns_headers_only(conn):
    send(conn, "POST", "/books", ORWELL)
    _, listing = send(conn, "GET", "/books")
    response, body = send(conn, "HEAD", "/books")
    assert response.status == 200
    assert body is None
    assert int(response.getheader("Content-Length")) == len(json.dumps(listing, ensure_ascii=False).encode())


def test_oversized_body_is_rejected(conn):
    headers = {"Content-Length": str(MAX_BODY_BYTES + 1), "Content-Type": "application/json"}
    response, body = send(conn, "POST", "/books", body=b"{}", headers=headers)
    assert response.status == 413
    assert "error" in body
    assert response.getheader("Connection") == "close"


def test_chunked_body_is_rejected(conn):
    conn.putrequest("POST", "/books")
    conn.putheader("Transfer-Encoding", "chunked")
    conn.endheaders()
    conn.send(b"2\r\n{}\r\n0\r\n\r\n")
    response = conn.getresponse()
    assert response.status == 411
    assert "error" in json.loads(response.read())


def test_stalled_body_times_out_with_408(conn, monkeypatch):
    monkeypatch.setattr(BooksRequestHandler, "timeout", 0.2)
    conn.putrequest("POST", "/books")
    conn.putheader("Content-Length", "50")
    conn.endheaders()
    conn.send(b'{"title": ')  # ...and never the rest
    response = conn.getresponse()
    assert response.status == 408
    assert "error" in json.loads(response.read())


def test_client_disconnecting_mid_body_does_not_break_the_server(server_address, conn):
    with socket.create_connection(server_address, timeout=5) as sock:
        sock.sendall(b"POST /books HTTP/1.1\r\nHost: x\r\nContent-Length: 100\r\n\r\n{\"title\"")
        sock.shutdown(socket.SHUT_WR)
        assert sock.recv(1024) == b""  # the server closes without a reply
    response, body = send(conn, "GET", "/books")
    assert (response.status, body) == (200, [])


def test_unsupported_method_gets_json_error(conn):
    response, body = send(conn, "BREW", "/books")
    assert response.status == 501
    assert response.getheader("Content-Type") == "application/json"
    assert "error" in body


def test_concurrent_clients(server_address):
    errors = []

    def client(n):
        connection = http.client.HTTPConnection(*server_address, timeout=10)
        try:
            for i in range(10):
                response, _ = send(connection, "POST", "/books", {"title": f"T{n}-{i}", "author": f"A{n}"})
                if response.status != 201:
                    errors.append(response.status)
        finally:
            connection.close()

    threads = [threading.Thread(target=client, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    connection = http.client.HTTPConnection(*server_address, timeout=5)
    _, books = send(connection, "GET", "/books")
    connection.close()
    assert len(books) == 80


# -- command-line entry point -------------------------------------------------


def start_cli_server(db_path, stderr_path):
    """Run `python -m books_api` on a free port. Returns (process, (host, port))."""
    with open(stderr_path, "wb") as stderr:  # the child keeps its own copy of the descriptor
        process = subprocess.Popen(
            [sys.executable, "-m", "books_api", "--host", "127.0.0.1", "--port", "0", "--db", str(db_path)],
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=stderr,
            text=True,
        )
    line = process.stdout.readline()
    match = re.search(r"http://([\d.]+):(\d+)", line)
    if not match:
        process.kill()
        process.wait()
        process.stdout.close()
        pytest.fail(f"server did not start: {line!r}\n{Path(stderr_path).read_text()}")
    return process, (match.group(1), int(match.group(2)))


def stop_cli_server(process):
    process.send_signal(signal.SIGTERM)
    try:
        return process.wait(timeout=10)
    finally:
        process.stdout.close()


@pytest.mark.skipif(sys.platform == "win32", reason="relies on POSIX SIGTERM delivery")
def test_cli_serves_and_persists_to_sqlite_file(tmp_path):
    db_path = tmp_path / "books.db"

    process, address = start_cli_server(db_path, tmp_path / "stderr-1.log")
    try:
        connection = http.client.HTTPConnection(*address, timeout=5)
        assert send(connection, "GET", "/health")[0].status == 200
        response, created = send(connection, "POST", "/books", ORWELL)
        assert response.status == 201
        connection.close()
    finally:
        assert stop_cli_server(process) == 0

    assert db_path.exists()

    # A fresh process on the same database file still has the book.
    process, address = start_cli_server(db_path, tmp_path / "stderr-2.log")
    try:
        connection = http.client.HTTPConnection(*address, timeout=5)
        assert send(connection, "GET", "/books")[1] == [created]
        connection.close()
    finally:
        assert stop_cli_server(process) == 0
