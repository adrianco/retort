# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `lib.rs:health` |
| POST | /books | `201 Book` \| `422` \| `400` | `lib.rs:create_book` |
| GET | /books | `200 [Book]` (optional `?author=` exact, case-insensitive) | `lib.rs:list_books` |
| GET | /books/{id} | `200 Book` \| `404` \| `400` | `lib.rs:get_book` |
| PUT | /books/{id} | `200 Book` \| `422` \| `404` \| `400` | `lib.rs:update_book` |
| DELETE | /books/{id} | `204` \| `404` \| `400` | `lib.rs:delete_book` |

## Library API

- `open_db(path: &str) -> rusqlite::Result<Connection>` — opens/initialises the SQLite DB (`:memory:` supported).
- `app(conn: Connection) -> Router` — builds the axum router with shared `Arc<Mutex<Connection>>` state.
- `Book`, `BookInput`, `ListParams`, `ApiError` — public types.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).

## Error format

JSON `{"error": "..."}`; validation failures add a `details` array. Codes: 400 (malformed JSON / non-integer id), 404 (not found), 422 (validation).
