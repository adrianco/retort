# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/bookapi/__init__.py | Package exports and version | `BookAPI`, `BookRepository`, `create_app`, `__version__` |
| src/bookapi/__main__.py | `python -m bookapi` launcher | delegates to `server.main` |
| src/bookapi/models.py | Frozen dataclasses for book data | `BookData`, `Book`, `Book.to_dict()` |
| src/bookapi/validation.py | Validate/normalise book payloads | `validate_book()`, `ValidationError`, `latest_year()` |
| src/bookapi/repository.py | SQLite CRUD storage layer | `BookRepository` (`create`/`get`/`list_books`/`update`/`delete`/`ping`/`close`), `DEFAULT_DATABASE` |
| src/bookapi/web.py | WSGI request/response/error helpers | `Request`, `Response`, `HTTPError`, `StartResponse` |
| src/bookapi/app.py | WSGI app, routing, request handlers | `BookAPI`, `create_app()` |
| src/bookapi/server.py | Threaded wsgiref server + CLI | `main()`, `make_book_server()`, `parse_args()`, `ThreadingWSGIServer`, `RequestHandler` |
| tests/conftest.py | Shared pytest fixtures | `repository`, `wsgi_app`, `client`, `make_client`, `run_concurrently`, `make_book` |
| tests/test_api.py | HTTP-level API integration tests | 55 test functions |
| tests/test_repository.py | Storage-layer unit tests | 25 test functions |
| tests/test_server.py | Live-server / HTTP protocol tests | 25 test functions |
| tests/test_validation.py | Validation unit tests | 20 test functions |
