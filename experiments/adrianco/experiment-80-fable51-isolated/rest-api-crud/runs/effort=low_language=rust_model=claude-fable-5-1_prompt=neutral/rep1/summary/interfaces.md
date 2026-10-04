# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `lib.rs:health` |
| POST | /books | `201 Book` \| `422` \| `400` | `lib.rs:create_book` |
| GET | /books | `200 [Book]` (optional `?author=` exact filter) | `lib.rs:list_books` |
| GET | /books/{id} | `200 Book` \| `404` | `lib.rs:get_book` |
| PUT | /books/{id} | `200 Book` \| `422` \| `404` | `lib.rs:update_book` |
| DELETE | /books/{id} | `204` \| `404` | `lib.rs:delete_book` |

## Library API (exported)

- `open_db(path: &str) -> rusqlite::Result<Connection>` — opens/creates the DB and ensures schema (`":memory:"` supported).
- `app(conn: Connection) -> Router` — builds the axum router with shared `Arc<Mutex<Connection>>` state.
- `Book { id, title, author, year: Option<i64>, isbn: Option<String> }` — public serializable model.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
