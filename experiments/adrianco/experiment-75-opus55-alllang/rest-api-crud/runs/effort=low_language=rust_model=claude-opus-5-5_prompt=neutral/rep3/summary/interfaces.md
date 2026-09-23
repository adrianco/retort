# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` | `lib.rs:health` |
| POST | /books | `Book` (201) / 400 | `lib.rs:create_book` |
| GET | /books | `[Book]` (200), `?author=` filter | `lib.rs:list_books` |
| GET | /books/{id} | `Book` (200) / 404 | `lib.rs:get_book` |
| PUT | /books/{id} | `Book` (200) / 400 / 404 | `lib.rs:update_book` |
| DELETE | /books/{id} | 204 / 404 | `lib.rs:delete_book` |

## Library API

- `open_db(path: &str) -> rusqlite::Result<Db>` — opens SQLite, creates `books` table, wraps in `Arc<Mutex<Connection>>`.
- `app(db: Db) -> Router` — builds the Axum router.
- `Book`, `BookInput`, `ListQuery`, `ApiError` — data + error types.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
