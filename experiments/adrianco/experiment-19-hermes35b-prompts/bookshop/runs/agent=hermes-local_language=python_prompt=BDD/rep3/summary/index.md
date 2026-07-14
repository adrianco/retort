# Architecture Summary — Book Collection REST API (Flask + SQLite, BDD)

## Modules

| File | Role | Key symbols |
|------|------|-------------|
| `app.py` | Flask HTTP layer — routes, request parsing, validation, status codes | `health`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book` |
| `models.py` | SQLite persistence layer | `get_db_connection`, `init_db`, `insert_book`, `select_all_books`, `select_book_by_id`, `update_book`, `delete_book`, `_row_to_dict` |
| `conftest.py` | pytest-bdd fixtures — `app_client` (fresh DB per test), `scenario_data` | — |
| `tests/features/*.feature` | Gherkin behaviour specs (6 features, 16 scenarios) | — |
| `tests/features/test_*.py` | pytest-bdd step definitions binding Gherkin → HTTP calls | — |

## Interfaces

REST/JSON over HTTP:
- `GET /health` → `{"status":"ok"}`, 200
- `POST /books` (title, author required; year, isbn optional) → 201 / 400
- `GET /books?author=` → 200 list
- `GET /books/{id}` → 200 / 404
- `PUT /books/{id}` → 200 / 400 / 404
- `DELETE /books/{id}` → 200 / 404

## Flow

HTTP request → `app.py` route → validation → `models.py` function → new `sqlite3` connection per call
(row_factory=Row) → SQL → `_row_to_dict` → `jsonify` response with status code. DB path from
`BOOKS_DB_PATH` env (default `books.db`); tests point it at a per-test `/tmp` file.

## Design notes

- Clean two-layer separation (transport vs persistence); no ORM, direct parameterised SQL (no injection risk).
- Connection-per-call is simple and correct for this scope (no pooling; acceptable for the task).
- BDD structure fully realised: each requirement expressed as Given-When-Then, exercised through the
  public HTTP interface, not internals — matching the BDD prompt factor.
