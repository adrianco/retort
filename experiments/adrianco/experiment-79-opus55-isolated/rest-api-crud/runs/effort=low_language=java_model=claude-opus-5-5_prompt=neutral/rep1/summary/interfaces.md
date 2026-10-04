# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status:"ok"}` (200) | `App.java:44` |
| POST | /books | `Book` (201) / error (400) | `App.java:46` |
| GET | /books | `[Book]` (200), `?author=` filter | `App.java:48` |
| GET | /books/{id} | `Book` (200) / `404` / `400` | `App.java:50` |
| PUT | /books/{id} | `Book` (200) / `404` / `400` | `App.java:55` |
| DELETE | /books/{id} | `204` / `404` / `400` | `App.java:60` |

Error bodies are JSON: `{"error": ...}` and, for validation, `{"error":"Validation failed","details":[...]}`. Unmatched routes return `{"error":"Not found"}`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable). Author filter uses `COLLATE NOCASE` for case-insensitive exact match.

## Library API

`BookRepository` — `create`, `list(author)`, `find(id)`, `update(id, book)`, `delete(id)`, `close()`; `AutoCloseable`.
