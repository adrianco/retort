# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/bookapi/app.py | WSGI app: routing + CRUD/health request handlers | `BookApp`, `create_app()` |
| src/bookapi/repository.py | SQLite-backed storage (schema, CRUD, ping) | `BookRepository`, `Book`, `DEFAULT_DATABASE` |
| src/bookapi/validation.py | Validate/normalise book payloads | `validate_book()`, `BookFields`, `ValidationError` |
| src/bookapi/web.py | Request/Response helpers, JSON encoding, body reading | `Request`, `Response`, `json_response()`, `HTTPError` |
| src/bookapi/server.py | CLI + `wsgiref` threaded server | `main()`, `build_parser()`, `ThreadingWSGIServer` |
| src/bookapi/__main__.py | `python -m bookapi` entry | `main` (re-export) |
| src/bookapi/__init__.py | Package marker | — |
| tests/conftest.py | Fixtures: client, app, file_client, live server | fixtures |
| tests/test_api.py | End-to-end HTTP/API integration tests | 55 test functions |
| tests/test_server.py | Server/CLI/argparse tests | 23 test functions |
| tests/test_repository.py | Repository/SQLite tests | 21 test functions |
| tests/test_validation.py | Payload validation tests | 16 test functions |
