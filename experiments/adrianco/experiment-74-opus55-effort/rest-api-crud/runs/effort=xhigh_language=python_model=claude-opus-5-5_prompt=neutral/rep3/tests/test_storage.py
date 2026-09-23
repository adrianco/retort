from books_api.storage import BookRepository

DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
EMMA = {"title": "Emma", "author": "Jane Austen", "year": 1815, "isbn": None}
PERSUASION = {"title": "Persuasion", "author": "Jane Austen", "year": 1817, "isbn": None}


def test_create_assigns_id_and_get_returns_book(repository):
    book = repository.create(DUNE)
    assert book == {"id": book["id"], **DUNE}
    assert repository.get(book["id"]) == book


def test_get_missing_book_returns_none(repository):
    assert repository.get(12345) is None


def test_list_all_returns_books_in_creation_order(repository):
    created = [repository.create(b) for b in (DUNE, EMMA, PERSUASION)]
    assert repository.list_all() == created


def test_list_all_filters_by_author_substring_case_insensitively(repository):
    repository.create(DUNE)
    emma = repository.create(EMMA)
    persuasion = repository.create(PERSUASION)
    assert repository.list_all(author="Jane Austen") == [emma, persuasion]
    assert repository.list_all(author="austen") == [emma, persuasion]
    assert repository.list_all(author="Tolkien") == []


def test_author_filter_folds_non_ascii_case(repository):
    book = repository.create({"title": "Cien años de soledad", "author": "GABRIEL GARCÍA MÁRQUEZ", "year": 1967, "isbn": None})
    assert repository.list_all(author="garcía márquez") == [book]


def test_author_filter_treats_sql_wildcards_literally(repository):
    repository.create(DUNE)
    assert repository.list_all(author="%") == []
    assert repository.list_all(author="_") == []


def test_update_replaces_fields(repository):
    book = repository.create(DUNE)
    updated = repository.update(book["id"], {**DUNE, "title": "Dune Messiah", "isbn": None})
    assert updated == {"id": book["id"], **DUNE, "title": "Dune Messiah", "isbn": None}
    assert repository.get(book["id"]) == updated


def test_update_missing_book_returns_none(repository):
    assert repository.update(999, DUNE) is None
    assert repository.list_all() == []


def test_delete(repository):
    book = repository.create(DUNE)
    assert repository.delete(book["id"]) is True
    assert repository.get(book["id"]) is None
    assert repository.delete(book["id"]) is False


def test_ids_of_deleted_books_are_not_reused(repository):
    first = repository.create(DUNE)
    repository.delete(first["id"])
    second = repository.create(DUNE)
    assert second["id"] > first["id"]


def test_data_persists_across_connections(tmp_path):
    db_path = tmp_path / "nested" / "books.db"
    repo = BookRepository(db_path)
    book = repo.create(DUNE)
    repo.close()

    reopened = BookRepository(db_path)
    try:
        assert reopened.list_all() == [book]
    finally:
        reopened.close()


def test_ping_reports_database_health(repository):
    assert repository.ping() is True
    repository.close()
    assert repository.ping() is False
