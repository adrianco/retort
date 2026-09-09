# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` after a `SELECT 1` | `lib.rs:health` |
| POST | /books | `201 Book` + `Location` header | `lib.rs:create_book` |
| GET | /books | `200 [Book]` (ordered by id) | `lib.rs:list_books` |
| GET | /books?author= | `200 [Book]` exact author match | `lib.rs:list_books` |
| GET | /books/{id} | `200 Book \| 404` | `lib.rs:get_book` |
| PUT | /books/{id} | `200 Book \| 404` | `lib.rs:update_book` |
| DELETE | /books/{id} | `204 \| 404` | `lib.rs:delete_book` |

Fallbacks: unknown route → `404`, wrong method → `405`. Errors are JSON `{"error": "..."}`.

## Library API

Exported from the `book_collection` crate: `app(Database) -> Router`, `Database::open(path)`, `Database::from_connection(Connection)`, and the `Book` struct.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL, non-blank CHECK), `author` (TEXT NOT NULL, non-blank CHECK), `year` (INTEGER, nullable), `isbn` (TEXT, nullable). Index `books_author` on `author`.
