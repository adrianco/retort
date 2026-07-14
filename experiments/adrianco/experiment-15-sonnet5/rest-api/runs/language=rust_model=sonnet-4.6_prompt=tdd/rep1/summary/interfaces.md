# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `handlers.rs:health` |
| POST | /books | `201 Book` \| `422 {error}` | `handlers.rs:create_book` |
| GET | /books | `200 [Book]` (supports `?author=`) | `handlers.rs:list_books` |
| GET | /books/:id | `200 Book` \| `404 {error}` | `handlers.rs:get_book` |
| PUT | /books/:id | `200 Book` \| `404 {error}` | `handlers.rs:update_book` |
| DELETE | /books/:id | `200 {"deleted":true}` \| `404 {error}` | `handlers.rs:delete_book` |

## Data schema

`books` table (SQLite): `id` (TEXT PK, UUID v4), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).

## Library API

- `build_app(conn: Connection) -> Router` — constructs the Axum router with shared `Arc<Mutex<Connection>>` state.
- `db::*` — free functions performing parameterized SQL CRUD.

## CLI commands

(none)
