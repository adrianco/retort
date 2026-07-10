"""
pytest-bdd conftest: shared fixtures for the Book Collection API tests.
"""
import os
import pytest
import models
import app as flask_app

@pytest.fixture
def app_client(request):
    """Test client with a fresh SQLite DB per test."""
    db_path = f"/tmp/test_books_{id(request)}.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    models.DB_PATH = db_path
    models.init_db()
    flask_app.app.config["TESTING"] = True
    with flask_app.app.test_client() as client:
        yield client
    if os.path.exists(db_path):
        os.remove(db_path)

@pytest.fixture
def scenario_data(request):
    """Shared data store for the current scenario."""
    data = {"response": None, "book_id": None, "books": []}
    yield data
