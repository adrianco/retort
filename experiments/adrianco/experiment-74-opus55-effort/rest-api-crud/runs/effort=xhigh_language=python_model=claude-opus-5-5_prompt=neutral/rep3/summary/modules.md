# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| books_api/__init__.py | Package root; WSGI app factory | `create_app()`, `BookAPI`, `BookRepository` |
| books_api/app.py | WSGI application, routing, request/response handling | `BookAPI`, `Response`, `HTTPError` |
| books_api/storage.py | SQLite persistence layer | `BookRepository` (create/get/list_all/update/delete/ping/close) |
| books_api/validation.py | Payload validation and normalisation | `validate_book()`, `BookFields`, `ValidationError` |
| books_api/server.py | Stdlib threaded WSGI server + CLI | `main()`, `create_server()`, `parse_args()` |
| books_api/__main__.py | `python -m books_api` entry point | module `__main__` |
| tests/conftest.py | Pytest fixtures (client, repository, server) | fixtures |
| tests/test_api.py | WSGI-level API integration tests | 33 test functions |
| tests/test_storage.py | Repository unit tests | 12 test functions |
| tests/test_validation.py | Validation unit tests | 17 test functions |
| tests/test_server.py | Over-HTTP + arg-parsing tests | 5 test functions |
| tests/test_cli.py | Subprocess/CLI lifecycle tests | 3 test functions |
