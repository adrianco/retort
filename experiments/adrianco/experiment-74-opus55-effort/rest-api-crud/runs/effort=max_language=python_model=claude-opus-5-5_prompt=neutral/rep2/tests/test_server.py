"""The ``python -m books_api`` entry point: a real server over HTTP, and its options."""

import http.client
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from books_api import __main__ as cli

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STARTUP_TIMEOUT_SECONDS = 30


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Server:
    def __init__(self, port):
        self.port = port

    def request(self, method, path, body=None):
        """Send one request; return ``(status, parsed JSON body or None)``."""
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            headers = {"Content-Type": "application/json"} if body is not None else {}
            payload = json.dumps(body).encode() if body is not None else None
            conn.request(method, path, body=payload, headers=headers)
            response = conn.getresponse()
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
        finally:
            conn.close()


@pytest.fixture
def server(tmp_path):
    port = _free_port()
    log_path = tmp_path / "server.log"
    command = [
        sys.executable, "-m", "books_api",
        "--host", "127.0.0.1", "--port", str(port), "--db", str(tmp_path / "books.db"),
    ]
    with log_path.open("w") as log:
        process = subprocess.Popen(command, cwd=PROJECT_ROOT, stdout=log, stderr=subprocess.STDOUT)
    try:
        server = Server(port)
        deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
        while True:
            try:
                if server.request("GET", "/health") == (200, {"status": "ok"}):
                    break
            except OSError:
                pass  # not listening yet
            if process.poll() is not None or time.monotonic() > deadline:
                pytest.fail(f"server did not start:\n{log_path.read_text()}")
            time.sleep(0.1)
        yield server
    finally:
        process.terminate()
        process.wait(timeout=10)


def test_serves_the_full_crud_cycle_over_http(server):
    dune = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}

    status, book = server.request("POST", "/books", dune)
    assert status == 201
    assert book == {"id": book["id"], **dune}

    assert server.request("GET", f"/books/{book['id']}") == (200, book)
    assert server.request("GET", "/books?author=herbert") == (200, [book])
    assert server.request("GET", "/books?author=Austen") == (200, [])

    status, updated = server.request("PUT", f"/books/{book['id']}", {**dune, "year": 1966})
    assert (status, updated["year"]) == (200, 1966)

    assert server.request("POST", "/books", {"author": "Anonymous"})[0] == 400
    assert server.request("DELETE", f"/books/{book['id']}") == (204, None)
    assert server.request("GET", f"/books/{book['id']}")[0] == 404
    assert server.request("GET", "/books") == (200, [])


@pytest.fixture
def uvicorn_run(monkeypatch):
    """Stand in for ``uvicorn.run``, recording what it was asked to serve."""
    calls = []
    monkeypatch.setattr(cli.uvicorn, "run", lambda app, **options: calls.append((app, options)))
    for name in ("BOOKS_API_HOST", "BOOKS_API_PORT", "BOOKS_API_DB"):
        monkeypatch.delenv(name, raising=False)
    return calls


def test_command_line_options_configure_the_server(uvicorn_run, tmp_path):
    cli.main(["--host", "0.0.0.0", "--port", "9000", "--db", str(tmp_path / "shelf.db")])

    [(app, options)] = uvicorn_run
    assert options == {"host": "0.0.0.0", "port": 9000}
    assert app.state.repository.path == str(tmp_path / "shelf.db")


def test_defaults_come_from_the_environment(uvicorn_run, monkeypatch, tmp_path):
    monkeypatch.setenv("BOOKS_API_HOST", "0.0.0.0")
    monkeypatch.setenv("BOOKS_API_PORT", "9001")
    monkeypatch.setenv("BOOKS_API_DB", str(tmp_path / "env.db"))

    cli.main([])

    [(app, options)] = uvicorn_run
    assert options == {"host": "0.0.0.0", "port": 9001}
    assert app.state.repository.path == str(tmp_path / "env.db")


def test_without_configuration_it_serves_books_db_on_localhost_8000(uvicorn_run):
    cli.main([])

    [(app, options)] = uvicorn_run
    assert options == {"host": "127.0.0.1", "port": 8000}
    assert app.state.repository.path == "books.db"


def test_empty_environment_variables_count_as_unset(uvicorn_run, monkeypatch):
    # An empty host would otherwise mean every network interface.
    for name in ("BOOKS_API_HOST", "BOOKS_API_PORT", "BOOKS_API_DB"):
        monkeypatch.setenv(name, "")

    cli.main([])

    [(app, options)] = uvicorn_run
    assert options == {"host": "127.0.0.1", "port": 8000}
    assert app.state.repository.path == "books.db"


@pytest.mark.parametrize(
    ("args", "env", "option"),
    [
        pytest.param(["--port", "http"], {}, "--port", id="--port not a number"),
        pytest.param(["--port", "0"], {}, "--port", id="--port zero"),
        pytest.param([], {"BOOKS_API_PORT": "99999"}, "--port", id="BOOKS_API_PORT out of range"),
        pytest.param(["--host", " "], {}, "--host", id="--host empty"),
        pytest.param(["--db", ":memory:"], {}, "--db", id="--db in memory"),
    ],
)
def test_an_invalid_option_is_a_usage_error(uvicorn_run, monkeypatch, capsys, args, env, option):
    for name, value in env.items():
        monkeypatch.setenv(name, value)

    with pytest.raises(SystemExit) as exit_info:
        cli.main(args)

    assert exit_info.value.code == 2
    assert f"argument {option}" in capsys.readouterr().err
    assert uvicorn_run == []
