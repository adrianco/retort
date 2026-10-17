# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| book_api/__init__.py | Package exports | `Book`, `BookFields`, `BookHTTPServer`, `BookRepository`, `create_server` |
| book_api/__main__.py | CLI entry point (`python -m book_api`) | `main()` |
| book_api/server.py | HTTP layer: routing, JSON responses, error mapping on `http.server` | `BookRequestHandler`, `BookHTTPServer`, `create_server()`, `Response`, `ApiError` |
| book_api/repository.py | SQLite-backed book storage | `BookRepository` (`create`/`get`/`list_books`/`update`/`delete`/`ping`/`close`) |
| book_api/validation.py | Payload validation + normalisation | `validate_book()`, `ValidationError` |
| book_api/models.py | Plain data objects | `Book`, `BookFields` |
| tests/conftest.py | Fixtures: in-memory repo, live server, JSON client | `repository`, `server`, `api`, `ApiClient` |
| tests/test_api.py | HTTP integration tests against a live server | 19 test functions |
| tests/test_repository.py | Repository/persistence unit tests | 8 test functions |
| tests/test_validation.py | Validation unit tests | 12 test functions |
