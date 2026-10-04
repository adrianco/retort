# Book Collection API

A small JSON REST service backed by SQLite and implemented with Python's standard library (WSGI).

## Run

Requires Python 3. The database defaults to `books.sqlite3` in the current directory; set `BOOKS_DATABASE` to choose another path.

```sh
python app.py
```

The service listens on `http://127.0.0.1:8000`.

## API

- `GET /health` returns `{"status":"ok"}`.
- `POST /books` accepts `title`, `author`, and optional `year`, `isbn`; returns the created record with status 201.
- `GET /books` lists records; `GET /books?author=NAME` filters by exact author.
- `GET /books/{id}` fetches one record.
- `PUT /books/{id}` replaces a record; `title` and `author` are required.
- `DELETE /books/{id}` deletes a record and returns 204.

Missing records return 404 and invalid JSON or required fields return 400. Responses use JSON except the empty 204 response.

## Tests

```sh
python -m pytest
```
