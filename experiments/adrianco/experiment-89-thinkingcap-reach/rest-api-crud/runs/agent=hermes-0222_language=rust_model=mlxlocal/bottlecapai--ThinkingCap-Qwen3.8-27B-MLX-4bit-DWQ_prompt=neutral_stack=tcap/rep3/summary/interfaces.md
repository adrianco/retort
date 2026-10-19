# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | / | `200 {service descriptor}` | `lib.rs:about` |
| GET | /health | `200 {"status":"ok"}` | `lib.rs:health` |
| POST | /books | `201 Book` / `400 {error}` | `lib.rs:create_book` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `lib.rs:list_books` |
| GET | /books/{id} | `200 Book` / `404 {error}` | `lib.rs:get_book` |
| PUT | /books/{id} | `200 Book` / `400` / `404` | `lib.rs:update_book` |
| DELETE | /books/{id} | `204` / `404 {error}` | `lib.rs:delete_book` |

## Library API (exported)

`Book`, `CreateBookRequest`, `UpdateBookRequest`, `ListBooksQuery`, `AppState`, `ApiError`, `init_db(path)`, `router(state)`, `validate_required(title, author)`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable). Backed by rusqlite with the `bundled` SQLite feature.
