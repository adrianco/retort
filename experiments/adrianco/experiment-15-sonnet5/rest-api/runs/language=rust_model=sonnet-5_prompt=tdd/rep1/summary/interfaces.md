# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `handlers.rs:health` |
| POST | /books | `201 Book` \| `400 {error}` | `handlers.rs:create_book` |
| GET | /books | `200 [Book]` (optional `?author=` LIKE filter) | `handlers.rs:list_books` |
| GET | /books/:id | `200 Book` \| `404 {error}` | `handlers.rs:get_book` |
| PUT | /books/:id | `200 Book` \| `400 {error}` \| `404 {error}` | `handlers.rs:update_book` |
| DELETE | /books/:id | `204 No Content` \| `404 {error}` | `handlers.rs:delete_book` |

## Data schema

`books` table (SQLite, `db.rs:init_db`): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER NOT NULL), `isbn` (TEXT NOT NULL). `PRAGMA journal_mode=MEMORY`.

## Library API

`app(conn: SharedConn) -> Router` builds the router; `SharedConn = Arc<Mutex<Connection>>`. `test_support::test_app()` returns a router backed by an in-memory SQLite DB for tests.

## Validation

`BookInput::validate()` rejects empty/whitespace `title` or `author` with a 400.
