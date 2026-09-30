"""Shared fixtures: an in-memory API and a tiny WSGI test client."""

from __future__ import annotations

import io
import json as jsonlib
import sys
import threading
import time
from pathlib import Path
from urllib.parse import unquote
from wsgiref.util import setup_testing_defaults
from wsgiref.validate import validator

import pytest

# Make ``src/`` importable even if pytest is started without picking up pyproject.toml.
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from bookapi import BookAPI, BookRepository  # noqa: E402

_UNSET = object()


class ClientResponse:
    def __init__(self, status_line, headers, body):
        self.status_code = int(status_line.split(" ", 1)[0])
        self.headers = {name.lower(): value for name, value in headers}
        self.body = body

    @property
    def text(self):
        return self.body.decode("utf-8")

    def json(self):
        return jsonlib.loads(self.body)


class Client:
    """Calls a WSGI application directly (no sockets).

    By default the app is wrapped in ``wsgiref.validate.validator``, so every test doubles
    as a PEP 3333 conformance check (status line, header types, hop-by-hop headers, ...).
    Pass ``validate=False`` to send requests the validator itself refuses to forward, such
    as a malformed Content-Length.
    """

    def __init__(self, app, *, validate=True):
        self._app = validator(app) if validate else app

    def request(self, method, target, *, json=_UNSET, data=None, content_type=None, environ=None):
        if json is not _UNSET:
            body, content_type = jsonlib.dumps(json).encode("utf-8"), "application/json"
        elif isinstance(data, str):
            body = data.encode("utf-8")
        else:
            body = data or b""

        # A PEP 3333 server hands over the request target decoded as latin-1.
        raw_path, _, query = target.encode("utf-8").decode("latin-1").partition("?")
        env = {}
        setup_testing_defaults(env)
        env.update(
            REQUEST_METHOD=method,
            PATH_INFO=unquote(raw_path, encoding="latin-1"),
            QUERY_STRING=query,
        )
        env["wsgi.input"] = io.BytesIO(body)
        if body:
            env["CONTENT_LENGTH"] = str(len(body))
        if content_type:
            env["CONTENT_TYPE"] = content_type
        env.update(environ or {})

        captured = {}

        def start_response(status, headers, exc_info=None):
            captured["status"], captured["headers"] = status, headers

        result = self._app(env, start_response)
        try:
            payload = b"".join(result)
        finally:
            if hasattr(result, "close"):
                result.close()
        return ClientResponse(captured["status"], captured["headers"], payload)

    def get(self, target, **kwargs):
        return self.request("GET", target, **kwargs)

    def post(self, target, **kwargs):
        return self.request("POST", target, **kwargs)

    def put(self, target, **kwargs):
        return self.request("PUT", target, **kwargs)

    def delete(self, target, **kwargs):
        return self.request("DELETE", target, **kwargs)

    def head(self, target, **kwargs):
        return self.request("HEAD", target, **kwargs)

    def options(self, target, **kwargs):
        return self.request("OPTIONS", target, **kwargs)


@pytest.fixture
def repository():
    with BookRepository(":memory:") as repo:
        yield repo


# Not called "app": pytest-flask's autouse fixtures hijack any fixture with that name.
@pytest.fixture
def wsgi_app(repository):
    return BookAPI(repository)


@pytest.fixture
def client(wsgi_app):
    return Client(wsgi_app)


@pytest.fixture
def make_client():
    """Factory for clients around a custom app: ``make_client(app, validate=False)``."""
    return Client


@pytest.fixture
def run_concurrently():
    """``run_concurrently(worker, count)`` runs ``worker(n)`` in ``count`` threads at once.

    Fails the test if a worker raises or is still running after ``timeout`` seconds, so a
    stall or deadlock shows up as a failure with a message rather than a silent hang.
    """

    def run(worker, count, timeout=30):
        errors = []

        def guarded(n):
            try:
                worker(n)
            except BaseException as exc:  # re-raised in the test's own thread below
                errors.append(exc)

        threads = [threading.Thread(target=guarded, args=(n,), daemon=True) for n in range(count)]
        for thread in threads:
            thread.start()
        deadline = time.monotonic() + timeout
        for thread in threads:
            thread.join(max(0.0, deadline - time.monotonic()))
        stuck = sum(thread.is_alive() for thread in threads)
        if stuck:
            pytest.fail(f"{stuck} of {count} worker threads are stuck after {timeout}s (deadlock?)")
        if errors:
            raise errors[0]

    return run


@pytest.fixture
def make_book(client):
    """Create a book through the API and return its JSON representation."""

    def _make(**fields):
        response = client.post(
            "/books", json={"title": "Dune", "author": "Frank Herbert", **fields}
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _make
