import threading

import pytest

from bookapi.server import create_server
from bookapi.store import BookStore


@pytest.fixture
def store():
    book_store = BookStore(":memory:")
    yield book_store
    book_store.close()


@pytest.fixture
def base_url(store):
    server = create_server(store, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join()
