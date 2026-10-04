# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` | `lib.rs:health` |
| GET | /books | `[Book]` (optional `?author=` filter) | `lib.rs:list_books` |
| POST | /books | `201 Book` + `Location` header \| `400` | `lib.rs:create_book` |
| GET | /books/{id} | `Book` \| `404` \| `400` (non-integer id) | `lib.rs:get_book` |
| PUT | /books/{id} | `Book` \| `404` \| `400` | `lib.rs:update_book` |
| DELETE | /books/{id} | `204` \| `404` | `lib.rs:delete_book` |
| * | (fallback) | `404 {"error":"not found"}` | inline closure |

## Library API

- `app(state: AppState) -> Router` — builds the router.
- `AppState::open(path: &str) -> rusqlite::Result<AppState>` — opens/creates the DB and schema (`:memory:` supported).
- `Book` — serializable record (`id, title, author, year?, isbn?`).
- `ApiError` — `Validation | BadRequest | NotFound | Internal`, each mapped to a JSON error response.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable). Index `idx_books_author` on `author`.
