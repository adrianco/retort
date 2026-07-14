"""Pytest configuration for the Book API acceptance tests.

Provides the clean_db fixture so that every test starts from an empty book collection.
"""
import pytest
import requests

BASE_URL = "http://127.0.0.1:5001"


@pytest.fixture(autouse=True)
def clean_db():
    """Clear all books from the collection before each test.

    Each scenario starts from an empty collection -- no data is shared between tests.
    """
    resp = requests.get(f"{BASE_URL}/books")
    books = resp.json()
    for book in books:
        requests.delete(f"{BASE_URL}/books/{book['id']}")
