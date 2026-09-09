# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `lib.rs` inline closure |
| GET | /books | `200 [Book]` (optional `?author=` exact filter) | `lib.rs:list` |
| POST | /books | `201 Book` + `Location` header | `lib.rs:create` |
| GET | /books/{id} | `200 Book \| 404` | `lib.rs:read` |
| PUT | /books/{id} | `200 Book \| 404` | `lib.rs:update` |
| DELETE | /books/{id} | `200 {"deleted":id} \| 404` | `lib.rs:delete` |

Fallbacks: unknown route → `404`; wrong method on a known path → `405`. Errors are JSON `{"error": "..."}`.

## Library API

- `Database::open(path)` — opens/creates the SQLite connection, sets a 5s busy timeout, runs the `books` table migration.
- `app(db: Database) -> Router` — builds the configured axum router.
- `Book { id, title, author, year: Option<i32>, isbn: Option<String> }` — serialized response type.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL, non-blank CHECK), `author` (TEXT NOT NULL, non-blank CHECK), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
