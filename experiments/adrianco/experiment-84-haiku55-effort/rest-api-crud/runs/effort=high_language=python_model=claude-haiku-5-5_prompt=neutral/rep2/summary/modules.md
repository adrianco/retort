# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| bookapi/__init__.py | Package docstring only | — |
| bookapi/__main__.py | CLI entry point; parses `--host/--port/--db`, builds store+server, serves | `main()` |
| bookapi/server.py | HTTP layer: routing, JSON encoding, error responses, request handler | `handle_request()`, `create_server()`, `Response`, `BookRequestHandler` |
| bookapi/store.py | SQLite persistence; lock-guarded shared connection | `BookStore` (`create`, `get`, `list_books`, `update`, `delete`, `ping`, `close`) |
| bookapi/validation.py | Payload validation/normalisation for book fields | `validate_book()`, `ValidationError` |
| tests/conftest.py | pytest fixtures: in-memory `store`, live `base_url` server | `store`, `base_url` fixtures |
| tests/test_api.py | End-to-end HTTP integration tests | 21 test functions |
| tests/test_store.py | Store-layer unit tests (incl. file persistence) | 6 test functions |
| tests/test_validation.py | Validation unit tests (parametrized) | 11 test functions |
