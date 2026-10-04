# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `lib.rs:health` |
| POST | /books | `201 Book` / `400` malformed / `422` validation | `lib.rs:create_book` |
| GET | /books | `200 [Book]` (`?author=` exact filter) | `lib.rs:list_books` |
| GET | /books/{id} | `200 Book` / `404` | `lib.rs:get_book` |
| PUT | /books/{id} | `200 Book` / `400` / `404` / `422` | `lib.rs:update_book` |
| DELETE | /books/{id} | `204` / `404` | `lib.rs:delete_book` |

## Library API

- `app(conn: Connection) -> Router` — builds the configured router.
- `open_db(path: &str) -> rusqlite::Result<Connection>` — opens/creates DB and schema (`":memory:"` supported).
- `Book { id, title, author, year: Option, isbn: Option }` — serialized entity.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL),
`author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
Index `idx_books_author` on `author`.
