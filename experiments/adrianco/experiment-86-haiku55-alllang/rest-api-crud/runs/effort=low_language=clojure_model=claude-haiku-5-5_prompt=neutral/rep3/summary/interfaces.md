# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status: "ok"}` (200) | `handler.clj:routes` |
| POST | /books | `Book` (201) \| errors (400) | `handler.clj:create` |
| GET | /books | `[Book]` (200), optional `?author=` exact filter | `handler.clj:list-all` |
| GET | /books/{id} | `Book` (200) \| 404 | `handler.clj:get-one` |
| PUT | /books/{id} | `Book` (200) \| 400 \| 404 | `handler.clj:update-one` |
| DELETE | /books/{id} | 204 \| 404 | `handler.clj:delete-one` |

Non-numeric ids (`/books/abc`) and unknown routes return 404. Malformed JSON bodies return 400 (via `wrap-json-body`).

## Data schema

`books` table (SQLite): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER), `isbn` (TEXT).

## Library API

`books.db` exposes a datasource-based CRUD API; `books.handler/app` wraps the raw router with JSON body/response and param middleware.
