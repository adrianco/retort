# Architecture Summary

Single-module Flask REST API (`app.py`, 167 LoC) backed by SQLite via Flask-SQLAlchemy, plus a pytest integration suite (`test_app.py`, 220 LoC) and a `README.md`.

## Modules

| File | Role |
|------|------|
| `app.py` | Application factory `create_app()`, `Book` model, all six CRUD routes + `/health`. |
| `test_app.py` | 14 pytest integration tests using a temp-file SQLite DB fixture. |
| `README.md` | Setup, run, and API usage documentation. |

## Design

- **Application factory** — `create_app(test_db_path=None)` builds the Flask app, binds SQLAlchemy, defines the `Book` model in closure scope, and returns `(app, db, Book)`. A module-level default instance is created for `python app.py`.
- **Model** — `Book`: `id` (PK, autoincrement), `title`/`author` (NOT NULL), `year`/`isbn` (nullable), `created_at`/`updated_at` (server-managed timestamps). `to_dict()` serializes for JSON.
- **Validation** — `_validate_book_payload()` enforces required `title`/`author`; `year` coerced to int with a 400 on failure.

## Routes / Interface

| Method | Path | Handler | Codes |
|--------|------|---------|-------|
| GET | `/health` | `health` | 200 |
| POST | `/books` | `create_book` | 201 / 400 |
| GET | `/books` (`?author=`) | `list_books` | 200 |
| GET | `/books/<int:id>` | `get_book` | 200 / 404 |
| PUT | `/books/<int:id>` | `update_book` | 200 / 400 / 404 |
| DELETE | `/books/<int:id>` | `delete_book` | 200 / 404 |

## Flow

Request → route handler → `_validate_book_payload` (writes) → SQLAlchemy session query/commit → `jsonify(book.to_dict())` with status code. Author filter uses case-insensitive `ILIKE %author%`.

## Notes

- Persistence is real SQLite (file `books.db`, or a temp file per test).
- No blueprints/service layer — appropriate for the task's scope.
