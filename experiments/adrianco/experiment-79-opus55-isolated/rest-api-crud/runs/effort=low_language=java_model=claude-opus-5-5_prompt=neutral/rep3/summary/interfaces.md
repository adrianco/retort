# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | 200 `{"status":"ok"}` | `BookServer:route` |
| POST | /books | 201 + book, `Location` header | `BookServer:route` → `repo.create` |
| GET | /books | 200 `[Book]`; `?author=` filters (case-insensitive) | `BookServer:route` → `repo.list` |
| GET | /books/{id} | 200 book \| 404 | `BookServer:route` → `repo.find` |
| PUT | /books/{id} | 200 book \| 404 | `BookServer:route` → `repo.update` |
| DELETE | /books/{id} | 204 \| 404 | `BookServer:route` → `repo.delete` |

Unknown paths → 404; unsupported methods → 405 with `Allow` header. Errors are JSON
(`{"error": ..., "details": [...]}`). Body over 1 MiB → 413.

## Data schema

`books` table: id (INTEGER pk autoincrement), title (TEXT NOT NULL), author (TEXT NOT NULL),
year (INTEGER, nullable), isbn (TEXT, nullable).

## Library API

- `BookRepository(jdbcUrl)` — `create`, `list(author)`, `find(id)`, `update(id, book)`, `delete(id)`, `close()`
- `BookServer(repo, port)` — `start()`, `stop()`, `port()`
- `Book(id, title, author, year, isbn)` record — `withId(newId)`
