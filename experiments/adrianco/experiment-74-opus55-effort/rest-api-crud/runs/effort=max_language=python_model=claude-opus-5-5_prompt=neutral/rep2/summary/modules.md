# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| books_api/app.py | HTTP routes and the application factory | `create_app()`, `app`, `router`, `BodySizeLimit` |
| books_api/db.py | SQLite storage: schema, CRUD, connection handling | `BookRepository`, `DatabaseUnavailable`, `MAX_ID` |
| books_api/schemas.py | Pydantic request/response models and validation | `BookIn`, `Book` |
| books_api/errors.py | RFC 9457 problem-details error handlers | `install_error_handlers()`, `problem_response()`, `Problem` |
| books_api/__main__.py | CLI entry point (host/port/db args + env) | `main()` |
| books_api/__init__.py | Package version | `__version__` |
| tests/conftest.py | Shared fixtures (per-test SQLite-backed client) | `client`, `db_path`, `add_book` |
| tests/test_api.py | API integration tests | 49 test functions |
| tests/test_repository.py | Repository/DB-layer tests | 8 test functions |
| tests/test_server.py | CLI / uvicorn wiring + live-server smoke test | 6 test functions |
