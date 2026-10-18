# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status: ok}` | `handler.clj:handle` |
| POST | /books | `201 Book` / `422` / `400` | `handler.clj:handle` → `db/create-book!` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `handler.clj:handle` → `db/list-books` |
| GET | /books/{id} | `200 Book` / `404` | `handler.clj:handle` → `db/get-book` |
| PUT | /books/{id} | `200 Book` / `404` / `422` / `400` | `handler.clj:handle` → `db/update-book!` |
| DELETE | /books/{id} | `204` / `404` | `handler.clj:handle` → `db/delete-book!` |

Other paths return `404`; unsupported methods on a known path return `405`; unhandled exceptions return `500`. All error bodies are JSON `{"error": "..."}` (with a `details` vector on validation errors).

## Data schema

`books` table (SQLite): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER), `isbn` (TEXT).

## Library API

- `books.db/datasource`, `create-book!`, `get-book`, `list-books` (1- and 2-arity), `update-book!`, `delete-book!`
- `books.handler/app` (builds the Ring handler), `validation-errors`

## CLI commands

(none) — a long-running server started via `clojure -M:run`.
