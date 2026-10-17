# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| POST | /books | `201` + `{id, title, author, year, isbn}` + `Location` header | `books.py:create_book` |
| GET | /books | `200` `[Book]`, optional `?author=` filter | `books.py:list_books` |
| GET | /books/{id} | `200` `Book` \| `404` | `books.py:get_book` |
| PUT | /books/{id} | `200` `Book` \| `400` \| `404` | `books.py:update_book` |
| DELETE | /books/{id} | `204` \| `404` | `books.py:delete_book` |
| GET | /health | `200` `{status, database}` \| `503` | `__init__.py:health` |

Unknown routes return JSON `404`; unsupported methods return JSON `405` with an `Allow` header (`errors.py:handle_http_error`).

## Data schema

`books` table (`db.py:SCHEMA`): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).

## Library API

- `create_app(test_config=None) -> Flask` — app factory.
- `validate_book(payload) -> dict` — returns cleaned fields or raises `ApiError(400)` naming every invalid field.
- `normalize_isbn(text) -> str | None` — ISBN-10/13 checksum validation, returns bare digits.
