# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET / HEAD | /health | `200 {status, database, books, uptime_seconds}` or `503` | book_api_health_h |
| GET / HEAD | /books | `200 [book]` (optional `?author=` case-insensitive exact filter) | book_api_books_h:list |
| POST | /books | `201 book` + `Location` header, or `400 validation_failed` | book_api_books_h:create |
| GET / HEAD | /books/:id | `200 book` or `404 not_found` | book_api_book_h:show |
| PUT | /books/:id | `200 book` (replace semantics), `400`, or `404` | book_api_book_h:update |
| DELETE | /books/:id | `204` (empty) or `404 not_found` | book_api_book_h:delete |
| (other methods) | above paths | `405 method_not_allowed` + `Allow` header | book_api_http:method_not_allowed |
| (any) | unmatched | `404 not_found` (JSON envelope) | book_api_notfound_h |

## Response envelopes

- Error: `{"error": Code, "message": Msg}`; validation errors add `"details": [{"field", "message"}]`.
- Book: `{"id", "title", "author", "year", "isbn", "created_at", "updated_at"}` — timestamps rendered as RFC3339 (Z) strings.

## Data schema

Mnesia `disc_copies` tables:

- `book` (`ordered_set`, keyed by `id`): `id` (pos_integer, pk), `title` (binary), `author` (binary), `year` (integer | null), `isbn` (binary | null), `created_at` (int seconds), `updated_at` (int seconds).
- `book_counter`: `name` (atom), `value` (integer) — id sequence bumped via `dirty_update_counter/3`.

## Validation rules (book:validate/1)

- `title`, `author`: required, non-blank binary strings, max 512 bytes.
- `year`: optional integer or null, range -3000..2999.
- `isbn`: optional string or null; structural ISBN-10/13 check (length + alphabet, no checksum); blank → null.

## Configuration

- Env vars `BOOK_API_PORT` (default 8080), `BOOK_API_DB_DIR` (default "data"); fall back to app env.

## CLI commands

(none)

## Library API

Exported for reuse/testing: `book:validate/1`, `book:to_map/1`, `book:matches_author/2`; full `book_store` CRUD API.
