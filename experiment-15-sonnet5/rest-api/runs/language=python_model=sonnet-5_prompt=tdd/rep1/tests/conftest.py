import os
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["BOOKS_DB_PATH"] = path

    from app import database
    from app.main import app

    database.init_db(path)

    with TestClient(app) as test_client:
        yield test_client

    os.remove(path)
