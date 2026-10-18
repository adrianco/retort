# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` 200 | `app.py:health` |
| POST | /books | `Book` 201 / 400 | `app.py:create_book` |
| GET | /books | `[Book]` 200 (`?author=` filter) | `app.py:list_books` |
| GET | /books/{id} | `Book` 200 / 404 | `app.py:get_book` |
| PUT | /books/{id} | `Book` 200 / 400 / 404 (partial updates) | `app.py:update_book` |
| DELETE | /books/{id} | empty 204 / 404 | `app.py:delete_book` |

## Data schema

`books` table: `id` (int, pk autoincrement), `title` (text, not null), `author` (text, not null), `year` (int, nullable), `isbn` (text, nullable).

## Library API

- `create_app(db_path=DEFAULT_DB_PATH) -> Flask` — app factory
- `init_db(db_path)` — creates the `books` table
- `parse_book_payload(data, partial=False) -> (fields, error)` — validation
