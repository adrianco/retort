# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/bookapi/app.py | WSGI application: routing + request handlers for the book API | `BookApp`, `create_app()` |
| src/bookapi/web.py | Request/response helpers for the WSGI layer (JSON body, size limits, errors) | `Request`, `Response`, `HTTPError` |
| src/bookapi/repository.py | SQLite-backed CRUD storage with Unicode-aware author folding | `BookRepository` |
| src/bookapi/validation.py | Validation/normalisation of client book payloads | `validate_book()`, `ValidationError` |
| src/bookapi/models.py | Plain frozen dataclasses shared across layers | `Book`, `BookInput` |
| src/bookapi/server.py | CLI entry point + threaded stdlib WSGI server | `main()`, `create_server()`, `build_parser()` |
| src/bookapi/__main__.py | `python -m bookapi` shim | `main` |
| tests/test_api.py | End-to-end API integration tests | 76 test functions |
| tests/test_server.py | Live-server / protocol-level tests | 42 test functions |
| tests/test_repository.py | Repository unit tests | 30 test functions |
| tests/test_validation.py | Validation unit tests | 24 test functions |
| tests/conftest.py | Pytest fixtures | (fixtures) |
| tests/support.py | Shared WSGI test client + helpers | `WSGIClient`, helpers |
