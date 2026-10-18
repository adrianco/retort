# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"ok"}` | `BookServer:route` |
| GET | /books | `200 [Book]` (optional `?author=` filter, case-insensitive) | `BookServer:listBooks` |
| POST | /books | `201 Book` + `Location` header, `400` on validation/JSON error | `BookServer:createBook` |
| GET | /books/{id} | `200 Book` \| `404` \| `400` (bad id) | `BookServer:getBook` |
| PUT | /books/{id} | `200 Book` \| `404` \| `400` | `BookServer:updateBook` |
| DELETE | /books/{id} | `204` \| `404` \| `400` | `BookServer:deleteBook` |

Unmatched paths → `404`; unsupported methods on a known path → `405`; DB/other errors → `500`.

## Library API

- `BookRepository(jdbcUrl)` — CRUD over SQLite; methods `synchronized` on a shared connection.
- `BookValidator.validate(BookRequest)` — returns a trimmed copy or throws `ValidationException` listing every problem.
- `BookValidator.isValidIsbn(String)` — ISBN-10/13 check-digit validation.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
