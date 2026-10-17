"""Unit tests for payload validation (no HTTP involved)."""

import pytest

from bookapi import ValidationError, validate_book


def test_normalises_whitespace_and_keeps_optional_fields():
    result = validate_book({"title": "  Dune ", "author": " Frank Herbert", "year": 1965, "isbn": "978"})
    assert result == {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978"}


def test_missing_required_fields_reported_together():
    with pytest.raises(ValidationError) as exc:
        validate_book({})
    assert exc.value.errors == {"title": "is required", "author": "is required"}


def test_current_year_plus_one_is_accepted_but_not_beyond():
    import datetime

    limit = datetime.date.today().year + 1
    assert validate_book({"title": "T", "author": "A", "year": limit})["year"] == limit
    with pytest.raises(ValidationError):
        validate_book({"title": "T", "author": "A", "year": limit + 1})
