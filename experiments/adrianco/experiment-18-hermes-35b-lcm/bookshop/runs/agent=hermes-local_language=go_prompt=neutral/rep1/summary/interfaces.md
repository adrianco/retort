# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status: ok}` | `handlers.go:Health` |
| GET | /books | `200 [Book]` (supports `?author=` filter) | `handlers.go:listBooks` |
| POST | /books | `201 Book` \| `400` validation | `handlers.go:createBook` |
| GET | /books/{id} | `200 Book` \| `404` | `handlers.go:getBook` |
| PUT | /books/{id} | `200 Book` \| `400` \| `404` | `handlers.go:updateBook` |
| DELETE | /books/{id} | `204` \| `404` | `handlers.go:deleteBook` |

Routing note: `/books` and `/books/` are registered as two `mux.HandleFunc` patterns in `main.go`, with method dispatch and ID parsing (`strconv.Atoi`) done inline. Non-matching methods return `405`. Malformed/empty IDs return `400`.

## Data schema

`books` table (SQLite): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER NOT NULL), `isbn` (TEXT NOT NULL). Opened with `PRAGMA journal_mode=WAL` and `PRAGMA foreign_keys=ON`. Runs against an in-memory database (`:memory:`).

## Request / response bodies

- `CreateBookRequest`: `{title, author, year, isbn}` (used for both POST and PUT).
- `Book`: `{id, title, author, year, isbn}`.
- Error body: `{error: string}`; validation failures return `{errors: [{field, message}]}`.

## Library API

`BookStore` exposes `CreateBook`, `GetAllBooks(authorFilter)`, `GetBookByID`, `UpdateBook`, `DeleteBook`, `Close`. `BookHandler` wraps a `*BookStore`.

## CLI commands

(none)
