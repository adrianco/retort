# Interfaces

## HTTP routes (as actually served by `main:app`)

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"healthy"}` | `main.py:health_check` |
| GET | /books | raw list of row tuples (JSON array) | `main.py:get_books` |

Routes the task requires but the served app does **not** declare: `POST /books`,
`GET /books/{id}`, `PUT /books/{id}`, `DELETE /books/{id}`, and the `?author=` filter on
`GET /books`. `GET /books` returns raw SQLite row tuples rather than JSON objects, and sets
no explicit status codes.

## Library API (unrouted, in `book_api.py`)

| Function | Behaviour |
|----------|-----------|
| `create_book(title, author, year, isbn)` | INSERT; raises on duplicate ISBN |
| `get_all_books(author=None)` | SELECT, optional author filter |
| `get_book_by_id(book_id)` | SELECT one or `None` |
| `update_book(book_id, ...)` | dynamic UPDATE, `False` if absent |
| `delete_book(book_id)` | DELETE, `False` if absent |
| `health_check()` | `{"status":"healthy"}` |

These implement the full CRUD contract but are never exposed over HTTP.

## Data schema

`books` table: `id` (int, pk autoincrement), `title` (text, not null), `author` (text, not
null), `year` (int), `isbn` (text, unique). Defined identically (and separately) in both
`main.py:init_db` and `book_api.py:init_db`; the DB file is `books.db`.
