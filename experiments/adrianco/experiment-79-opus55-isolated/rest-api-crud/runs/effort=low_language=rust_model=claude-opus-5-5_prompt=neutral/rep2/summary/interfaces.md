# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status:"ok"}` (200) | `lib.rs:health` |
| POST | /books | `Book` (201) / 422 / 400 | `lib.rs:create_book` |
| GET | /books | `[Book]` (200), `?author=` filter | `lib.rs:list_books` |
| GET | /books/{id} | `Book` (200) / 404 | `lib.rs:get_book` |
| PUT | /books/{id} | `Book` (200) / 404 / 422 / 400 | `lib.rs:update_book` |
| DELETE | /books/{id} | 204 / 404 | `lib.rs:delete_book` |

## Data schema

`books` table: id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER, nullable), isbn (TEXT, nullable). Index `idx_books_author` on author.

## Library API

`app(db: Db) -> Router`, `Db::open(path)`, `Db::in_memory()`, `Book`, `BookInput`, `ApiError`.

## Error responses

JSON `{error: ...}`; 400 (bad/malformed JSON or wrong type), 404 (missing id), 422 (missing/blank title or author, with `details` array).
