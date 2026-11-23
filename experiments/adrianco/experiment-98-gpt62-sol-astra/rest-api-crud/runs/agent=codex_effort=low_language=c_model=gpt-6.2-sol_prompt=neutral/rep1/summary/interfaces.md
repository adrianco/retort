# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | 200 `{"status":"ok"}` | `books.c:route` |
| GET | /books | 200 `[Book]` (optional `?author=` exact filter) | `books.c:books` |
| POST | /books | 201 `Book` + `Location` header | `books.c:books` |
| GET | /books/{id} | 200 `Book` \| 404 | `books.c:books` |
| PUT | /books/{id} | 200 `Book` \| 404 | `books.c:books` |
| DELETE | /books/{id} | 204 \| 404 | `books.c:books` |

Unsupported methods on a known path return 405 with an `Allow` header. Invalid
JSON body or invalid `{id}` returns 400. All non-204 responses are
`application/json`; errors carry an `error` field.

## Data schema

`books` table (SQLite): `id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL,
`author` TEXT NOT NULL, `year` INTEGER (nullable), `isbn` TEXT (nullable).

## Library API

(none — single-binary service)

## CLI

`book-api [port] [database-file]` — port defaults to 8080, database defaults to
`books.db`; binds `127.0.0.1`.
