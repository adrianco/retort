# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | `/health` | `200 {"status":"ok"}` after a `SELECT 1` connectivity check | `app.py:87 health` |
| POST | `/books` | `201 Book` + `Location` header, or `400`/`415` | `app.py:92 create_book` |
| GET | `/books` | `200 [Book]` ordered by id; optional exact `?author=` filter | `app.py:101 list_books` |
| GET | `/books/{id}` | `200 Book` or `404` | `app.py:110 get_book` |
| PUT | `/books/{id}` | `200 Book` (full replace) or `400`/`404` | `app.py:114 update_book` |
| DELETE | `/books/{id}` | `204` empty body, or `404` | `app.py:123 delete_book` |

Every `HTTPException` — including 404/405/415 raised by routing and content
negotiation — is rendered as `{"error": "<description>"}` by the
`app.py:50 http_error` handler.

## Library API

- `app.py:11 create_app(test_config=None)` — application factory. Reads
  `DATABASE` from config (default `$BOOKS_DATABASE` or `books.sqlite3`);
  `":memory:"` is rewritten to a per-app private shared-cache URI database kept
  alive by a keeper connection (`app.py:22-24`).

## CLI commands

(none — `python app.py` runs the Flask dev server on 127.0.0.1:5000.)

## Data schema

`books` table (`app.py:40-46`):

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `title` | TEXT | NOT NULL, `length(trim(title)) > 0` |
| `author` | TEXT | NOT NULL, `length(trim(author)) > 0` |
| `year` | INTEGER | nullable |
| `isbn` | TEXT | nullable |
