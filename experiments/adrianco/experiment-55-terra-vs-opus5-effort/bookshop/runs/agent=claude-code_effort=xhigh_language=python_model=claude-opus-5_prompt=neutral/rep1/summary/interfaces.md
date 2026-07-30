# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | / | service description JSON | `routes.py:index` |
| GET | /health | `200 {status,version,database,books}` \| `503` | `routes.py:health` |
| POST | /books | `201 Book` + `Location` header \| `400` \| `409` | `routes.py:create_book` |
| GET | /books | `200 [Book]` + `X-Total-Count`; `?author=`, `?limit=`, `?offset=` | `routes.py:list_books` |
| GET | /books/{id} | `200 Book` \| `404` | `routes.py:get_book` |
| PUT | /books/{id} | `200 Book` (full replace) \| `404` \| `400` | `routes.py:replace_book` |
| PATCH | /books/{id} | `200 Book` (partial) \| `404` \| `400` | `routes.py:update_book` |
| DELETE | /books/{id} | `204` \| `404` | `routes.py:delete_book` |

## Data schema

`books` table: `id` (int, pk autoincrement), `title` (text, not null), `author`
(text, not null), `year` (int, nullable), `isbn` (text, unique, nullable),
`created_at` (text, not null), `updated_at` (text, not null). Index
`idx_books_author` on `author COLLATE NOCASE`.

## Error body

All failures render as `{"error": "<code>", "message": "<text>", "details": {...}?}`
via `errors.py:register_error_handlers` (ApiError, HTTPException, and catch-all
Exception handlers).

## CLI commands

`flask init-db` (`db.py:init_db_command`) — creates the books table.

## Library API

`bookapi.create_app(config)` — Flask application factory.
