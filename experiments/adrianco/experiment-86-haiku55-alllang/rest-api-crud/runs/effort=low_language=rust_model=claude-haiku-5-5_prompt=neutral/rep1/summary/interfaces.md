# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `lib.rs:health` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `lib.rs:list_books` |
| POST | /books | `201 Book` \| `400 {"error":...}` | `lib.rs:create_book` |
| GET | /books/{id} | `200 Book` \| `404` | `lib.rs:get_book` |
| PUT | /books/{id} | `200 Book` \| `400` \| `404` | `lib.rs:update_book` |
| DELETE | /books/{id} | `204` \| `404` | `lib.rs:delete_book` |

## Library API

- `app(state: AppState) -> Router` — builds the router
- `AppState::open(path)`, `AppState::in_memory()` — construct state + create schema
- `Book`, `BookInput`, `ListQuery`, `ApiError`

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
