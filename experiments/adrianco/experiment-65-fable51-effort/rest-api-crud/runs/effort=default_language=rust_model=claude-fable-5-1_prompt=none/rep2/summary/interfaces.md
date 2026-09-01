# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"ok"}` | `handlers.rs:health` |
| POST | /books | `201 Book` \| `400` \| `409` | `handlers.rs:create_book` |
| GET | /books | `200 [Book]` (optional `?author=`) | `handlers.rs:list_books` |
| GET | /books/{id} | `200 Book` \| `404` \| `400` | `handlers.rs:get_book` |
| PUT | /books/{id} | `200 Book` \| `400` \| `404` | `handlers.rs:update_book` |
| DELETE | /books/{id} | `204` \| `404` \| `400` | `handlers.rs:delete_book` |

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL),
`author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT UNIQUE, nullable).
Index `idx_books_author` on `author`.

## Library API (`books_api`)

`app(AppState) -> Router`, `AppState::new(Connection)`, `db::*` persistence functions,
`models::{Book, BookInput, ValidBook, ListQuery}`, `error::ApiError`.
