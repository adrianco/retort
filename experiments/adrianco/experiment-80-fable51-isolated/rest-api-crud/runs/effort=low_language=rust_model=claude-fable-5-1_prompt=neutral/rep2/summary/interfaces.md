# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `lib.rs:health` |
| POST | /books | `201 Book` / `422` validation / `400` malformed JSON | `lib.rs:create_book` |
| GET | /books | `200 [Book]` (optional `?author=` exact-match filter) | `lib.rs:list_books` |
| GET | /books/{id} | `200 Book` / `404` | `lib.rs:get_book` |
| PUT | /books/{id} | `200 Book` / `422` / `404` | `lib.rs:update_book` |
| DELETE | /books/{id} | `204` / `404` | `lib.rs:delete_book` |

## Library API (exported)

- `open_db(path: &str) -> rusqlite::Result<Db>` — open/create SQLite DB and ensure schema (`:memory:` supported)
- `app(db: Db) -> Router` — build the axum router with state
- `Book`, `BookInput`, `ListParams`, `ApiError`, `Db` (type alias `Arc<Mutex<Connection>>`)

## Data schema

`books` table: `id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL, `author` TEXT NOT NULL, `year` INTEGER (nullable), `isbn` TEXT (nullable).
