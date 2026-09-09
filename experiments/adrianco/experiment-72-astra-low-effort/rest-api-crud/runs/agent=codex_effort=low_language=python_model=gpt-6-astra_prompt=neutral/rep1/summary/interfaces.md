# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | `/health` | 200 `{"status":"ok"}` after a `SELECT 1` probe | `app.py:75 health` |
| POST | `/books` | 201 `Book` + `Location` header; 400 on invalid body; 415 on non-JSON content type | `app.py:80 create_book` |
| GET | `/books` | 200 `[Book]` ordered by id; `?author=` exact, case-sensitive filter | `app.py:92 list_books` |
| GET | `/books/{id}` | 200 `Book` \| 404 `{"error":"Book not found"}` | `app.py:102 get_book` |
| PUT | `/books/{id}` | 200 replaced `Book` \| 400 invalid body \| 404 missing | `app.py:109 update_book` |
| DELETE | `/books/{id}` | 200 `{"deleted": id}` \| 404 missing | `app.py:122 delete_book` |

Errors are uniformly JSON `{"error": "..."}` via two handlers: `HTTPException` → `app.py:44 http_error` (preserves the HTTP code) and `ValueError` → `app.py:66 validation_error` (400).

## CLI commands

`python app.py` starts the Flask development server on `127.0.0.1:5000` (`app.py:134`). No argument parsing.

## Library API

`create_app(config=None)` — application factory; `config` overrides `DATABASE` (also readable from the `BOOKS_DATABASE` env var, `app.py:15`).

## Data schema

`books` table (`app.py:33-41`): `id INTEGER PRIMARY KEY AUTOINCREMENT`, `title TEXT NOT NULL`, `author TEXT NOT NULL`, `year INTEGER`, `isbn TEXT`.
