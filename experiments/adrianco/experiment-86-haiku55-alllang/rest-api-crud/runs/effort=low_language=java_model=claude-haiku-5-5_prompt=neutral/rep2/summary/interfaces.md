# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status} 200` / `503` | `BookServer.handleHealth` |
| POST | /books | `Book 201` / `400` | `BookServer.handleCreate` |
| GET | /books | `[Book] 200`, optional `?author=` filter (case-insensitive) | `BookServer.handleList` |
| GET | /books/{id} | `Book 200` / `404` / `400` (non-numeric id) | `BookServer.handleGet` |
| PUT | /books/{id} | `Book 200` / `400` / `404` | `BookServer.handleUpdate` |
| DELETE | /books/{id} | `204` / `404` | `BookServer.handleDelete` |

Unknown routes → 404; unsupported methods → 405 with an `Allow` header.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable). Backed by SQLite via `sqlite-jdbc`.

## Library API

- `BookRepository` — `create`, `findById`, `findAll(author)`, `update`, `delete`, `ping`, `close` (AutoCloseable).
- `BookValidator.validate(Book)` → `List<String>` of errors.
- `Book` record with `withId(long)`.
