# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status, database}` \| `503` | `app.py:health` |
| GET | /books | `200 [Book]` (optional `?author=` substring filter) | `app.py:list_books` |
| POST | /books | `201 Book` + `Location` header \| `400` \| `415` | `app.py:create_book` |
| GET | /books/{id} | `200 Book` \| `404` | `app.py:get_book` |
| PUT | /books/{id} | `200 Book` (full replace) \| `400` \| `404` \| `415` | `app.py:update_book` |
| DELETE | /books/{id} | `200 {id, deleted}` \| `404` | `app.py:delete_book` |

Cross-cutting: unknown route → JSON `404`; unsupported method → JSON `405` with `Allow` header; body > 64 KB → `413`; non-JSON `Content-Type` → `415`.

## Data schema

`books` table (SQLite, `AUTOINCREMENT`): `id` (int, pk), `title` (text, not null), `author` (text, not null), `year` (int, nullable), `isbn` (text, nullable).

## Library API

- `app.create_app(config=None) -> Flask` — application factory (tests inject a temp DB path).
- `validation.validate_book(payload) -> dict` — raises `ValidationError` listing every invalid field.
- `db.*` — connection-per-request CRUD helpers over `flask.g`.
