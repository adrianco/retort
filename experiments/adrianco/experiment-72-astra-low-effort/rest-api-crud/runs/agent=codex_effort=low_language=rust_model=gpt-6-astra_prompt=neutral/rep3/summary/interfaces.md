# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | 200 `{"status":"ok"}` (after `SELECT 1`) | `lib.rs:health` |
| POST | /books | 201 `Book` + `Location` header | `lib.rs:create_book` |
| GET | /books | 200 `[Book]` (optional `?author=` exact filter) | `lib.rs:list_books` |
| GET | /books/{id} | 200 `Book` \| 404 | `lib.rs:get_book` |
| PUT | /books/{id} | 200 `Book` \| 404 | `lib.rs:update_book` |
| DELETE | /books/{id} | 200 `{"deleted":id}` \| 404 | `lib.rs:delete_book` |
| * | (unmatched) | 404 / 405 via fallbacks | `lib.rs:app` fallbacks |

## Library API

- `Database::open(path)`, `Database::in_memory()` — construct the connection pool (single `Arc<Mutex<Connection>>`), create the `books` table.
- `app(Database) -> Router` — the configured Axum router, used by both `main.rs` and tests.
- `Book { id, title, author, year: Option<i32>, isbn: Option<String> }` — serialized response model.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL, CHECK non-blank), `author` (TEXT NOT NULL, CHECK non-blank), `year` (INTEGER nullable), `isbn` (TEXT nullable).
