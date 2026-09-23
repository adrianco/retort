import json
from typing import Any, NamedTuple

import pytest

from books_api import BookRepository, BooksApp

_NO_BODY = object()


class Result(NamedTuple):
    status: int
    json: Any
    headers: dict[str, str]


@pytest.fixture
def repo():
    with BookRepository(":memory:") as repository:
        yield repository


@pytest.fixture
def app(repo):
    return BooksApp(repo)


@pytest.fixture
def call(app):
    """Send a request straight to ``BooksApp.handle`` and decode the JSON body.

    The body goes through a real JSON round trip, so the tests also check that
    every response serialises.
    """

    def _call(method: str, target: str, payload: Any = _NO_BODY, *, raw: bytes | None = None) -> Result:
        if raw is not None:
            body = raw
        elif payload is _NO_BODY:
            body = b""
        else:
            body = json.dumps(payload).encode()
        response = app.handle(method, target, body)
        data = json.loads(response.body) if response.body else None
        return Result(response.status, data, response.headers)

    return _call
