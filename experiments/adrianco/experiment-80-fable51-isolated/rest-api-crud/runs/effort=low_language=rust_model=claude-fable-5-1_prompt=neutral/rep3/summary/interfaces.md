# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `lib.rs:health` |
| POST | /books | `201 Book` \| `400 {error}` | `lib.rs:create_book` |
| GET | /books | `200 [Book]` (optional `?author=` exact filter) | `lib.rs:list_books` |
| GET | /books/{id} | `200 Book` \| `400` \| `404 {error}` | `lib.rs:get_book` |
| PUT | /books/{id} | `200 Book` \| `400` \| `404 {error}` | `lib.rs:update_book` |
| DELETE | /books/{id} | `204` \| `400` \| `404 {error}` | `lib.rs:delete_book` |

## Library API

`open_db(path: &str) -> rusqlite::Result<Connection>` — opens/initializes the DB (`:memory:` supported).
`app(conn: Connection) -> Router` — builds the axum router with shared `Arc<Mutex<Connection>>` state.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
