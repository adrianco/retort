# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `app.py:health` |
| POST | /books | `201 Book` \| `400` | `app.py:create_book` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `app.py:list_books` |
| GET | /books/{id} | `200 Book` \| `404` | `app.py:get_book` |
| PUT | /books/{id} | `200 Book` \| `400` \| `404` | `app.py:update_book` |
| DELETE | /books/{id} | `200 {"message":...}` \| `404` | `app.py:delete_book` |

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable). Stored in file-backed SQLite via stdlib `sqlite3` (path from `BOOKS_DB` env or `books.db`).

## Library API

`create_app(db_path=None)` returns a configured Flask app; module-level `app` is created at import for `flask run` / `python app.py`.
