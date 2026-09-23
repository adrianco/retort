# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status, database}` or `503` | `app.py:BooksApp._health` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `app.py:BooksApp._list_books` |
| POST | /books | `201 Book` + `Location` header, or `400` | `app.py:BooksApp._create_book` |
| GET | /books/{id} | `200 Book` or `404` | `app.py:BooksApp._get_book` |
| PUT | /books/{id} | `200 Book`, `400`, or `404` | `app.py:BooksApp._update_book` |
| DELETE | /books/{id} | `204` or `404` | `app.py:BooksApp._delete_book` |
| OPTIONS | (any matched path) | `204` + `Allow` header | `app.py:BooksApp._dispatch` |
| HEAD | (GET-capable paths) | GET response without body | `app.py:BooksApp._dispatch` |

Unmatched paths return `404`; unsupported methods on a matched path return `405` with an `Allow` header.

## Library API

- `BooksApp(repository).handle(method, target, body) -> Response` — socket-free request entry point.
- `BookRepository(path=":memory:")` — CRUD over SQLite; `create_book`, `list_books(author=None)`, `get_book`, `update_book`, `delete_book`, `ping`, `close`.
- `validate_book(payload, *, partial=False) -> dict` — raises `ValidationError` (with per-field `errors`).
- `create_server(app, host, port)` / `main(argv)` — HTTP transport + CLI.

## CLI

`books-api` (or `python -m books_api`) with `--host`, `--port` (0 = any free port), `--db` (file or `:memory:`); each also reads an env var (`BOOKS_API_HOST`, `BOOKS_API_PORT`, `BOOKS_DB_PATH`).

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
