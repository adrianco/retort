# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | 200 `{"status":"ok"}` | `BooksAPI.m:routeMethod:` |
| POST | /books | 201 book, 400 validation | `BooksAPI.m:createBook:` |
| GET | /books | 200 `[book]` (optional `?author=` exact, case-insensitive filter) | `BooksAPI.m:listBooks:` |
| GET | /books/{id} | 200 book, 404 | `BooksAPI.m:getBook:` |
| PUT | /books/{id} | 200 book, 400 validation, 404 | `BooksAPI.m:updateBook:body:` |
| DELETE | /books/{id} | 204, 404 | `BooksAPI.m:deleteBook:` |

Cross-cutting: unknown paths → 404; unsupported method on a known path → 405 with an `Allow` header; malformed headers → 400; body over 1 MB → 413; oversized headers → 431. All bodies are JSON; errors are `{"error": ...}` with an added `details` array on validation failures.

## Data schema

`books` table (SQLite): `id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL, `author` TEXT NOT NULL, `year` INTEGER (nullable), `isbn` TEXT (nullable).

## Library API

- `BooksAPI handleMethod:path:query:body:` → `APIResponse` (thread-safe via `@synchronized`).
- `APIResponse` value object: `status`, `body` (JSON `NSData`), `allow`, `json`.
- `BookStore` CRUD methods returning Foundation dictionaries/arrays with `NSError**` out-params.

## CLI commands

(none) — configured via `PORT`, `HOST`, `DB_PATH` environment variables.
