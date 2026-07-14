# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"healthy"}` | `lib.rs:health` |
| POST | /books | `201 Book` / `400` | `lib.rs:create_book` |
| GET | /books | `200 [Book]` (optional `?author=`) | `lib.rs:get_books` |
| GET | /books/{id} | `200 Book` / `404` | `lib.rs:get_book` |
| PUT | /books/{id} | `200 Book` / `404` | `lib.rs:update_book` |
| DELETE | /books/{id} | `204` / `404` | `lib.rs:delete_book` |

## Data schema

`books` table: id (INTEGER pk autoincrement), title (TEXT not null), author (TEXT not null), year (INTEGER not null), isbn (TEXT not null). Created inline in `init_pool` via `CREATE TABLE IF NOT EXISTS`; the identical `migrations/0001_init.sql` is never read.

## Library API

`book_api` crate exports the models, `BookError`, `init_pool()`, and the six handler functions (re-used by `main.rs`).
