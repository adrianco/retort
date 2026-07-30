# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | WSGI entry point; builds `app` and runs the dev server | `app`, `main()` |
| bookapi/__init__.py | Application factory; config, error handlers, blueprint wiring | `create_app()` |
| bookapi/routes.py | HTTP layer: routes, request parsing, response shaping | `bp`, route handlers |
| bookapi/repository.py | Data access for the `books` table (parameterised SQL) | `list_books`, `create_book`, `get_book`, `update_book`, `delete_book` |
| bookapi/db.py | SQLite connection lifecycle + schema bootstrap | `get_db()`, `init_app()`, `ping()` |
| bookapi/validation.py | Payload + query-string validation/normalisation | `validate_book_payload`, `validate_list_query` |
| bookapi/errors.py | ApiError hierarchy + JSON error handlers | `ApiError`, `ValidationError`, `NotFoundError`, `register_error_handlers` |
| bookapi/openapi.py | Hand-written OpenAPI 3.0 spec served at `/openapi.json` | `build_spec()` |
| tests/test_crud.py | CRUD happy/edge paths | 17 test functions |
| tests/test_listing.py | Listing filter/sort/page | 28 test functions |
| tests/test_validation.py | Payload/query validation | 27 test functions |
| tests/test_errors.py | Error rendering + status codes | 12 test functions |
| tests/test_persistence.py | SQLite persistence behaviour | 11 test functions |
| tests/test_openapi.py | OpenAPI spec | 5 test functions |
| tests/test_health.py | Health endpoint | 4 test functions |
| tests/conftest.py, tests/samples.py | Fixtures + sample data | (support) |
