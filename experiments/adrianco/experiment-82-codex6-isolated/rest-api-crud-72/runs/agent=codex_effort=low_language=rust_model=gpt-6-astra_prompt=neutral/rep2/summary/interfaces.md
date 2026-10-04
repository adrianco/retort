# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` (after a DB `SELECT 1`) | `lib.rs:health` |
| GET | /books | `200 [Book]` (optional `?author=` exact filter) | `lib.rs:list_books` |
| POST | /books | `201 Book` + `Location` header \| 400 \| 415 | `lib.rs:create_book` |
| GET | /books/{id} | `200 Book \| 404 \| 400` | `lib.rs:get_book` |
| PUT | /books/{id} | `200 Book \| 404 \| 400` | `lib.rs:update_book` |
| DELETE | /books/{id} | `204 \| 404 \| 400` | `lib.rs:delete_book` |
| * | (unmatched) | `404` route not found / `405` method not allowed | fallbacks |

Error bodies are `{"error": "message"}`.

## Library API

- `app(connection: Connection) -> rusqlite::Result<Router>` — builds the router over an existing SQLite connection, initializing the schema.
- `Book { id, title, author, year: Option<i32>, isbn: Option<String> }` — serialized response type.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL, CHECK trimmed length > 0), `author` (TEXT NOT NULL, CHECK trimmed length > 0), `year` (INTEGER, nullable), `isbn` (TEXT, nullable). Index `books_author` on `author`.
