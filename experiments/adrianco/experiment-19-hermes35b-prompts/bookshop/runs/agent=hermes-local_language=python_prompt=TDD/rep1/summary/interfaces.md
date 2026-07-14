# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` (200) | `app.py:health` |
| GET | /books | `[Book]` (200), supports `?author=` partial filter | `app.py:list_books` |
| POST | /books | `Book` (201) \| `{error}` (400) | `app.py:create_book` |
| GET | /books/{id} | `Book` (200) \| `{error}` (404) | `app.py:get_book` |
| PUT | /books/{id} | `Book` (200) \| `{error}` (400/404) | `app.py:update_book` |
| DELETE | /books/{id} | `{message}` (200) \| `{error}` (404) | `app.py:delete_book` |

## Data schema

`books` table (SQLite): id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL),
author (TEXT NOT NULL), year (INTEGER), isbn (TEXT).

## Library API

`create_app(db_path=None) -> Flask` — app factory. `get_db()` — per-request
connection cached on Flask `g`. `init_db()` — creates schema idempotently.
