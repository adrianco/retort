# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"ok"}` | `handlers.rs:health` |
| POST | /books | `201 Book \| 400` | `handlers.rs:create_book` |
| GET | /books | `200 [Book]` (optional `?author=`) | `handlers.rs:list_books` |
| GET | /books/:id | `200 Book \| 404` | `handlers.rs:get_book` |
| PUT | /books/:id | `200 Book \| 400 \| 404` | `handlers.rs:update_book` |
| DELETE | /books/:id | `204 \| 404` | `handlers.rs:delete_book` |

## Library API

- `book_api::app(pool: Pool) -> axum::Router` — builds the wired router.
- `book_api::db::init_pool(path: &str) -> Pool` — pool + schema; `:memory:` supported.
- `book_api::models::BookInput::validate()` — required-field check.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).

## Configuration

- `BOOK_API_DB` env var → sqlite file path (default `books.db`).
- `BOOK_API_ADDR` env var → bind address (default `0.0.0.0:3000`).
