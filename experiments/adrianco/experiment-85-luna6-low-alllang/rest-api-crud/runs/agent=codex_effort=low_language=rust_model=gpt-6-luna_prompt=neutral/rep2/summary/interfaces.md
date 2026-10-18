# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | inline closure (`main.rs:68`) |
| POST | /books | `201 Book` \| `400` | `main.rs:create_book` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `main.rs:list_books` |
| GET | /books/{id} | `200 Book` \| `404` | `main.rs:get_book` |
| PUT | /books/{id} | `200 Book` \| `400` \| `404` | `main.rs:update_book` |
| DELETE | /books/{id} | `204` \| `404` | `main.rs:delete_book` |

## Data schema

`books` table (SQLite): `id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL, `author` TEXT NOT NULL, `year` INTEGER (nullable), `isbn` TEXT (nullable).

## Library API

- `app() -> Router` — opens `books.db` and builds the router.
- `build_app(Connection) -> rusqlite::Result<Router>` — testable factory used with an in-memory connection.

Error responses use `{"error": "..."}` JSON via the `HttpError` IntoResponse impl.
