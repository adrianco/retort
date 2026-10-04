# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| bookapi/__init__.py | Package facade re-exporting the public API | `BookAPI`, `BookStore`, `create_app` |
| bookapi/app.py | WSGI app, routing, JSON I/O, error mapping, threaded server | `BookAPI`, `create_app()`, `make_threaded_server()`, `HTTPError` |
| bookapi/store.py | SQLite persistence for the `books` table | `BookStore` |
| bookapi/validation.py | Validation of book payloads | `validate_book()`, `ValidationError` |
| bookapi/__main__.py | CLI to run the server (`python -m bookapi`) | `main()` |
| tests/conftest.py | In-process WSGI client + fixtures | `Client`, `Response`, `app`, `client` fixtures |
| tests/test_api.py | In-process API integration tests | 30 test functions |
| tests/test_server.py | End-to-end tests over a real socket/DB file | 3 test functions |
