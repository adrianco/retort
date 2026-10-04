# Codebase summary: rest-api-crud (python, fable-5.1, effort=low, rep3)

`run-summary` skill not separately invocable here; concise manual summary follows.

## Modules

- **`app.py`** (200 LOC) — the whole service, standard-library only (`wsgiref`
  + `sqlite3`), no external dependencies.
  - `STATUS` / `ApiError` — status-code table and a typed HTTP error carrying
    `status`, `message`, optional `details`.
  - `validate_book(data)` — input validation: `title`/`author` required non-empty
    strings; `year` optional int (bool rejected); `isbn` optional string. Raises
    `ApiError(400, ..., details)` on failure.
  - `BookApp` — WSGI application object.
    - Data access: `create_book`, `list_books(author=None)`, `_get`,
      `update_book`, `delete_book` over a single SQLite connection guarded by a
      `threading.Lock`.
    - HTTP layer: `_read_json` (Content-Length bounded by `MAX_BODY`), `_route`
      (dispatch by method + path, `/books/{id}` via regex), `__call__` (maps
      `ApiError`→status, unexpected→500 with rollback).
  - `main()` — runs `wsgiref.simple_server`, configurable via `HOST`/`PORT`/`BOOKS_DB`.
- **`test_app.py`** (108 LOC) — 9 `unittest` tests driving the WSGI app in-process
  against an in-memory SQLite DB (`:memory:`).

## Flow

Request → `__call__` (acquires lock) → `_route` dispatches to the data-access
method → JSON-encodes payload with the mapped HTTP status. Errors are funnelled
through `ApiError`; unexpected exceptions roll back and return 500.

## Notes

- Persistence is real SQLite with an auto-increment PK and `NOT NULL` on
  title/author.
- `?author=` filter is exact, case-insensitive (`COLLATE NOCASE`).
- PUT is a full replace (requires title+author), consistent with the spec.
