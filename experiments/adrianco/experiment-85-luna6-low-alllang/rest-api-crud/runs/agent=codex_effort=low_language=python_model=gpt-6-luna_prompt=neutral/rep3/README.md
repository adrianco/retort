# Book Collection API

A small REST API written in Python using only the standard library. Books are stored in SQLite.

## Run

Python 3.9 or newer is required.

```sh
python app.py
```

The service listens at `http://127.0.0.1:8000`. Set `HOST`, `PORT`, or `BOOKS_DATABASE` to configure the bind address, port, or SQLite file.

## Endpoints

- `GET /health` returns `{"status":"ok"}`.
- `POST /books` accepts JSON with `title`, `author`, and optional `year`, `isbn`.
- `GET /books` lists books. Use `?author=Name` for an exact author filter.
- `GET /books/{id}` retrieves one book.
- `PUT /books/{id}` replaces a book's fields using the same JSON format.
- `DELETE /books/{id}` deletes a book.

Responses use JSON. Invalid input returns 400; missing books return 404; successful creation returns 201 and successful deletion returns 204.

## Tests

```sh
python -m pip install pytest
python -m pytest
```
