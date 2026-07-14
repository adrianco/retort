"""
Unit tests for Book API REST Service.

Focus on internal behaviour: model creation, validation, factory function,
and error handling. These are lighter-weight than the acceptance tests and
exercise implementation details directly.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app import create_app, Book, db


# ─── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def client():
    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ─── 1. Application factory ─────────────────────────────────────────────────


class TestAppFactory:
    """Test the create_app factory function."""

    def test_factory_returns_flask_app(self):
        """The factory returns a Flask app instance."""
        app = create_app()
        assert app is not None

    def test_factory_registers_routes(self):
        """The app has all expected routes registered."""
        app = create_app()
        rules = {rule.rule for rule in app.url_map.iter_rules()}
        assert "/health" in rules
        assert "/books" in rules


# ─── 2. Book model ──────────────────────────────────────────────────────────


class TestBookModel:
    """Test the Book SQLAlchemy model."""

    def test_create_book_model(self):
        """A Book model instance can be created with required fields."""
        book = Book(title="Test Book", author="Test Author")
        assert book.title == "Test Book"
        assert book.author == "Test Author"
        assert book.year is None
        assert book.isbn is None

    def test_create_book_model_with_all_fields(self):
        """A Book model instance can be created with all fields."""
        book = Book(title="Test Book", author="Test Author", year=2024, isbn="123")
        assert book.title == "Test Book"
        assert book.author == "Test Author"
        assert book.year == 2024
        assert book.isbn == "123"

    def test_to_dict_returns_dict(self):
        """The model's to_dict() method returns a dictionary."""
        book = Book(title="Book", author="Author", year=2020, isbn="isbn123")
        d = book.to_dict()
        assert isinstance(d, dict)
        assert d["title"] == "Book"
        assert d["author"] == "Author"
        assert d["year"] == 2020
        assert d["isbn"] == "isbn123"

    def test_to_dict_missing_optional_fields(self):
        """to_dict() handles missing optional fields gracefully."""
        book = Book(title="Book", author="Author")
        d = book.to_dict()
        assert d["year"] is None
        assert d["isbn"] is None


# ─── 3. Input validation at model level ─────────────────────────────────────


class TestValidation:
    """Test that required fields are enforced."""

    def test_create_with_db_requires_title(self, client):
        """Creating a book without title in DB raises integrity error."""
        app = client.application
        with app.app_context():
            try:
                book = Book(author="Just author")
                db.session.add(book)
                db.session.commit()
            except Exception:
                db.session.rollback()
            # Query should find no books because the insert failed
            assert Book.query.count() == 0

    def test_create_with_db_requires_author(self, client):
        """Creating a book without author in DB raises integrity error."""
        app = client.application
        with app.app_context():
            try:
                book = Book(title="Just title")
                db.session.add(book)
                db.session.commit()
            except Exception:
                db.session.rollback()
            assert Book.query.count() == 0
