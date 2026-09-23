# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"ok"}` | `BookAPI.m:handleMethod` |
| POST | /books | `201 Book \| 400` | `BookAPI.m:handleMethod` → `BookStore:createBook:` |
| GET | /books | `200 [Book]` (optional `?author=` exact filter) | `BookAPI.m:handleMethod` → `BookStore:listBooksByAuthor:` |
| GET | /books/{id} | `200 Book \| 404 \| 400` | `BookAPI.m:handleMethod` → `BookStore:bookWithId:` |
| PUT | /books/{id} | `200 Book \| 400 \| 404` | `BookAPI.m:handleMethod` → `BookStore:updateBook:with:` |
| DELETE | /books/{id} | `204 \| 404` | `BookAPI.m:handleMethod` → `BookStore:deleteBook:` |

Unmatched methods return `405`; unmatched paths `404`. Oversized bodies (>1 MiB) return `413`.

## Library API

- `BookStore` — SQLite-backed data access (`createBook:`, `listBooksByAuthor:`, `bookWithId:`, `updateBook:with:`, `deleteBook:`).
- `BookAPI` — `handleMethod:target:body:` maps an HTTP method/target/body to an `APIResponse`.
- `APIResponse` — `status` (NSInteger) + `body` (JSON object); `jsonData` serializes the body.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
