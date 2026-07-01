import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from app.database import get_connection, init_db
from app.main import app, get_db


@pytest.fixture()
def client():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    def get_test_db():
        conn = get_connection(db_path)
        try:
            init_db(conn)
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_db] = get_test_db
    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    os.remove(db_path)
