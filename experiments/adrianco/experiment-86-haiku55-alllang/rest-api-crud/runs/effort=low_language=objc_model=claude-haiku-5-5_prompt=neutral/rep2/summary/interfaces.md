# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:ok}` | `BookAPI.m:handleRequest:` |
| GET | /books | `200 [Book]` (optional `?author=`) | `BookAPI.m:listBooks:` |
| POST | /books | `201 Book` + `Location` / `400` | `BookAPI.m:createBook:` |
| GET | /books/{id} | `200 Book` / `400` / `404` | `BookAPI.m:getBook:` |
| PUT | /books/{id} | `200 Book` (merge update) / `400` / `404` | `BookAPI.m:updateBook:request:` |
| DELETE | /books/{id} | `204` / `404` | `BookAPI.m:deleteBook:` |

Unmatched method on a known path returns `405` with an `Allow` header; unknown path returns `404`.

## Library API

- `Book +bookFromDictionary:error:` — validates/parses JSON into a `Book` (title & author required, year integer, isbn string).
- `BookStore` — `insertBook:`, `bookWithID:`, `booksByAuthor:`, `updateBook:`, `deleteBookWithID:` over SQLite.
- `HTTPServer -initWithPort:handler:` — generic socket server taking a request→response block.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER null), `isbn` (TEXT null). Case-insensitive index on `author`.
