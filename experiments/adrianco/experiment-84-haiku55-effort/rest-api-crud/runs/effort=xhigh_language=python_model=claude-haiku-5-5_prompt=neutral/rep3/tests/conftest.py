import threading

import pytest

from bookapi import BookApi, BookRepository, make_server


@pytest.fixture
def repository():
    repo = BookRepository(":memory:")
    yield repo
    repo.close()


@pytest.fixture
def api(repository):
    return BookApi(repository)


@pytest.fixture
def live_server(api):
    """Run the real HTTP server on a free port for the duration of a test."""
    server = make_server(api, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
