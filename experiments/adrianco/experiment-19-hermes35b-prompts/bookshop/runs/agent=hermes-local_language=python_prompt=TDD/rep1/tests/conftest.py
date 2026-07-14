"""Pytest fixtures shared across all tests."""
import pytest
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture
def app():
    """Create application for testing.
    
    Creates a Flask app with a test SQLite database,
    clears all data before each test.
    """
    os.environ['DATABASE_PATH'] = "/tmp/test_books.db"
    
    # Remove test db if it exists
    if os.path.exists("/tmp/test_books.db"):
        os.remove("/tmp/test_books.db")
    
    from app import create_app
    app = create_app("/tmp/test_books.db")
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        yield app, client
    
    # Cleanup after test
    if os.path.exists("/tmp/test_books.db"):
        os.remove("/tmp/test_books.db")
    if os.path.exists("/tmp/test_books.db-wal"):
        os.remove("/tmp/test_books.db-wal")
    if os.path.exists("/tmp/test_books.db-shm"):
        os.remove("/tmp/test_books.db-shm")
