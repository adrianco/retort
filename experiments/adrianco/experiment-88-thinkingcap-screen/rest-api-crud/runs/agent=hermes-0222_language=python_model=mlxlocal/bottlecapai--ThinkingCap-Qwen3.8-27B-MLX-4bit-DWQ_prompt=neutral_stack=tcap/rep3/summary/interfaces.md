# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `app.py:health` |
| POST | /books | `201 Book` / `400 {error}` | `app.py:create_book` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `app.py:list_books` |
| GET | /books/{id} | `200 Book` / `404 {error}` | `app.py:get_book` |
| PUT | /books/{id} | `200 Book` / `400` / `404 {error}` | `app.py:update_book` |
| DELETE | /books/{id} | `204` / `404 {error}` | `app.py:delete_book` |

Global JSON error handlers: `404 {"error":"Not found"}`, `405 {"error":"Method not allowed"}`.

## Data schema

`books` table (SQLite): `id` (int, pk autoincrement), `title` (text, not null),
`author` (text, not null), `year` (int, nullable), `isbn` (text, nullable).

## Library API

`create_app(db_path=None)` — application factory; `db_path` defaults to `$BOOKS_DB`
or `books.db`. Used both by `main()` and by the test fixture with a tmp DB.
