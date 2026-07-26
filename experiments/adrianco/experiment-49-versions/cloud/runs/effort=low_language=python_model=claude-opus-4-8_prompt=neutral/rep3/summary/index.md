# Architecture summary — book-collection REST API

Single-module Flask app (`app.py`, 184 LOC) plus a pytest suite (`test_app.py`, 7 tests).

## Modules
- **app.py** — WSGI app factory `create_app(db_path)`. Private helpers `_connect`,
  `_init_db`, `_book_to_dict`, `_validate`. Six routes registered on the app.
- **test_app.py** — pytest fixture `client` builds an in-memory app; 7 test functions
  cover health, create, validation, get/404, list+filter, update, delete.

## Data layer
- Standard-library `sqlite3`, `books` table (id PK AUTOINCREMENT, title/author NOT NULL,
  year, isbn). File-backed `books.db` by default; `:memory:` uses a single shared
  connection kept alive for the app's lifetime (correct handling of in-memory scope).

## Request flow
POST/PUT run payload through `_validate` (type + non-empty checks) → 400 on error;
persist → re-select → return JSON. GET/DELETE resolve by id with 404 on miss.
Status codes: 201 create, 200 read/update, 204 delete, 400 validation, 404 not found.
