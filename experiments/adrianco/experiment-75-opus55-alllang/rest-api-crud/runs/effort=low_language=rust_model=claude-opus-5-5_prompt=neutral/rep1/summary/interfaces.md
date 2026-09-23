# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` (200) | `lib.rs:health` |
| GET | /books | `[Book]` (200), optional `?author=` exact filter | `lib.rs:list_books` |
| POST | /books | `Book` (201) / `{error}` (400) | `lib.rs:create_book` |
| GET | /books/{id} | `Book` (200) / `{error}` (404) | `lib.rs:get_book` |
| PUT | /books/{id} | `Book` (200) / 400 / 404 | `lib.rs:update_book` |
| DELETE | /books/{id} | 204 / 404 | `lib.rs:delete_book` |

## Library API

- `open_db(path: &str) -> rusqlite::Result<Db>` — opens SQLite connection, creates `books` table.
- `app(db: Db) -> Router` — builds the Axum router with all routes and shared state.
- `Db = Arc<Mutex<Connection>>` — shared connection handle.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).

## Configuration (env)

- `DATABASE_PATH` (default `books.db`), `BIND_ADDR` (default `0.0.0.0:3000`).
