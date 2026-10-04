# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | 200 `{"status":"ok"}` | `books_handler:handle(health, ...)` |
| POST | /books | 201 book + `Location` header; 400 bad JSON; 422 validation | `books_handler` collection |
| GET | /books | 200 `[book]`; `?author=` exact-match filter | `books_handler` collection → `books_db:list/1` |
| GET | /books/{id} | 200 book; 400 bad id; 404 | `books_handler` item → `books_db:get/1` |
| PUT | /books/{id} | 200 book (full replace); 400/404/422 | `books_handler` item → `books_db:update/2` |
| DELETE | /books/{id} | 204 no body; 400 bad id; 404 | `books_handler` item → `books_db:delete/1` |

Unsupported methods on a known path return 405 with an `Allow` header. Errors are JSON `{"error": ...}`, with a per-field `details` map on 422.

## Library API (books_db)

`create/1`, `list/1` (author `undefined` = no filter), `get/1`, `update/2`, `delete/1`, `delete_all/0` (test helper).

## Data schema

`books` table: `id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL, `author` TEXT NOT NULL, `year` INTEGER (nullable), `isbn` TEXT (nullable).
