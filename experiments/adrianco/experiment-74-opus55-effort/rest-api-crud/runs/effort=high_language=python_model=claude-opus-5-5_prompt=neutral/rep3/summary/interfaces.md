# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status, database}` \| `503` | `app.py:_health` |
| POST | /books | `201 Book` (+ Location) \| `400` \| `409` | `app.py:_create_book` |
| GET | /books | `200 [Book]` (optional `?author=`) | `app.py:_list_books` |
| GET | /books/{id} | `200 Book` \| `404` | `app.py:_get_book` |
| PUT | /books/{id} | `200 Book` \| `400` \| `404` \| `409` | `app.py:_update_book` |
| DELETE | /books/{id} | `204` \| `404` | `app.py:_delete_book` |

Unmatched paths → `404`; unsupported methods → `405` with an `Allow` header.

## Library API

`validate_book(payload) -> dict` (raises `ValidationError`);
`BookRepository` (`create`, `list`, `get`, `update`, `delete`, `ping`, `close`);
`make_server(repo, host, port, quiet)`.

## Data schema

`books` table: `id` (int, pk autoincrement), `title` (text, not null),
`author` (text, not null), `year` (int, nullable), `isbn` (text, unique nullable).
Index `idx_books_author` on `author COLLATE NOCASE`.
