# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | 200 `{status:ok}` / 503 `{status:unavailable}` | `BookAPI.m:health` |
| POST | /books | 201 `Book` + `Location` header / 400 | `BookAPI.m:createBook:` |
| GET | /books | 200 `[Book]` (optional `?author=` filter) | `BookAPI.m:listBooks:` |
| GET | /books/{id} | 200 `Book` / 400 (bad id) / 404 | `BookAPI.m:getBook:` |
| PUT | /books/{id} | 200 `Book` / 400 / 404 (full replacement) | `BookAPI.m:updateBook:request:` |
| DELETE | /books/{id} | 204 / 400 / 404 | `BookAPI.m:deleteBook:` |

Unmatched paths return 404; unsupported verbs on a matched path return 405 with an `Allow` header.

## Library API

- `Book bookFromJSONObject:error:` — validates a decoded JSON body (title+author required, year 0–9999 optional int, isbn optional string) into a `Book`.
- `BookStore` — `insertBook:`, `bookWithId:`, `booksByAuthor:`, `updateBook:`, `deleteBookWithId:`, `ping:`, over SQLite (file or `:memory:`).
- `BookAPI handleRequest:` — socket-independent router (directly unit-testable).
- `HTTPServer` — generic handler-block server; `HTTPRequestCreate()` parses a request target into path + decoded query.

## Data schema

`books` table (SQLite): `id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL, `author` TEXT NOT NULL, `year` INTEGER NULL, `isbn` TEXT NULL.
