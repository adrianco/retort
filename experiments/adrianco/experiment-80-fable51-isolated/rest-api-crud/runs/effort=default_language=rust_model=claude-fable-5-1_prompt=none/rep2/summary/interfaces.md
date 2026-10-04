# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status:"ok"}` (200) | `lib.rs:health` |
| POST | /books | `Book` (201) / 422 / 400 | `lib.rs:create_book` |
| GET | /books | `[Book]` (200), `?author=` exact filter | `lib.rs:list_books` |
| GET | /books/{id} | `Book` (200) / 404 | `lib.rs:get_book` |
| PUT | /books/{id} | `Book` (200) / 404 / 422 / 400 | `lib.rs:update_book` |
| DELETE | /books/{id} | 204 / 404 | `lib.rs:delete_book` |

## Library API

- `app(conn: Connection) -> rusqlite::Result<Router>` — builds the router on an open connection.
- `init_db(conn: &Connection) -> rusqlite::Result<()>` — creates the schema + author index.
- `Book` — serializable record; `AppState` — shared `Arc<Mutex<Connection>>`; `ApiError` — error enum with `IntoResponse`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable). Index `idx_books_author` on `author`.
