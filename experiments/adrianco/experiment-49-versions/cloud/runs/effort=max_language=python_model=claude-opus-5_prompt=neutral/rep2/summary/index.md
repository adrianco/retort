# Architecture Summary — book_api

A small Flask REST service for a book collection, backed by SQLite. Cleanly
layered: HTTP → validation → repository → SQLite, with a shared error model.

## Modules

| Module | Responsibility |
|--------|----------------|
| `book_api/__init__.py` | Application factory `create_app()`; env-driven config (database, max page size, body limit, ISBN-checksum flag, SQLite timeout). Registers db, error handlers, routes blueprint. |
| `book_api/routes.py` | HTTP layer. Endpoints: `GET /`, `GET /health`, `POST /books`, `GET /books`, `GET /books/<id>`, `PUT /books/<id>`, `PATCH /books/<id>`, `DELETE /books/<id>`. |
| `book_api/validators.py` | Validates request bodies (`parse_book_payload`) and list query strings (`parse_list_query`); collects all field errors into one `ValidationError`. ISBN shape + optional checksum. |
| `book_api/repository.py` | `BookRepository` — all SQL (parameterised). Reads/writes, filtering, sorting, pagination, integrity-guard translating `IntegrityError` → `ConflictError`. |
| `book_api/db.py` | SQLite connection lifecycle. Per-request connection for file DBs (WAL); single locked shared connection for `:memory:`. Schema DDL + `init-db` CLI. |
| `book_api/models.py` | Frozen `Book` dataclass; `from_row` / `to_dict`. |
| `book_api/errors.py` | `ApiError` hierarchy (Validation/NotFound/Conflict) + JSON error handlers for `ApiError`, `HTTPException`, and unexpected exceptions. |
| `book_api/utils.py` | `utcnow_iso()`, `current_year()`. |
| `wsgi.py`, `book_api/__main__.py` | WSGI entry point and `python -m book_api` dev CLI. |

## Request flow

`request → routes.<endpoint> → validators.parse_* → BookRepository (SQLite) →
Book.to_dict() → jsonify`. Errors raised anywhere in that chain are rendered by
the registered handlers into a uniform `{error, message, details}` JSON body
with the correct status code.

## Notable design choices

- Application-factory + blueprint structure; config entirely env-overridable.
- Pagination/sort/`q` search and `PATCH` are provided **beyond** the spec.
- Parameterised SQL throughout; `LIKE` wildcards escaped; unique partial index
  on normalised ISBN → `409 Conflict`.
- In-memory DB correctness handled explicitly (shared-cache URI + lock).

## Tests

102 test functions across 7 files (`tests/`), run against an in-memory DB via
`conftest.py` fixtures. No skipped/xfail tests. `test_coverage = 0.96`.
