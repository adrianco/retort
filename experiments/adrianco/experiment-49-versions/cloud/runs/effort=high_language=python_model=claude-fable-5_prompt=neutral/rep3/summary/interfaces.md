# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `app.py:health` |
| POST | /books | `201 Book` / `400 {errors}` | `app.py:create_book` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `app.py:list_books` |
| GET | /books/{id} | `200 Book` / `404` | `app.py:get_book` |
| PUT | /books/{id} | `200 Book` / `400` / `404` | `app.py:update_book` |
| DELETE | /books/{id} | `204` / `404` | `app.py:delete_book` |

Error handlers registered for `404` and `405` returning JSON.

## Data schema

`books` table: `id` (int, pk autoincrement), `title` (text, not null), `author` (text, not null), `year` (int, nullable), `isbn` (text, nullable).

## CLI commands

(none)

## Library API

`create_app(db_path=DEFAULT_DB_PATH)` — application factory returning a configured Flask app. `DB_PATH` overridable via `BOOKS_DB` env var; server port via `PORT`.
