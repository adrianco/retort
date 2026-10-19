# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `BookApiHandler.handle` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `BookApiHandler.handle` → `store.list` |
| POST | /books | `201 Book` + `Location` header (`400` on invalid) | `BookApiHandler.handle` → `store.create` |
| GET | /books/{id} | `200 Book \| 404` | `BookApiHandler.handle` → `store.get` |
| PUT | /books/{id} | `200 Book` (`400` invalid, `404` missing) | `BookApiHandler.handle` → `store.update` |
| DELETE | /books/{id} | `204 \| 404` | `BookApiHandler.handle` → `store.delete` |

Unknown paths → `404`; unsupported method on a known path → `405` with `Allow` header; unhandled error → `500`. Errors render as `{"error": "..."}`.

## Library API

- `BookStore(jdbcUrl)` — `create`, `list(author)`, `get(id)`, `update(id,...)`, `delete(id)`, `close()`
- `BookValidation.validate(BookInput)` / `require(value, field)`
- `Json.write(obj)`, `Json.readBookInput(bytes)`, `Json.error(msg)`

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable). `PRAGMA journal_mode=WAL`.
