# Book Collection API

A small REST service for storing books in SQLite. It uses only Python's standard
library, so no package installation is required.

## Run

Requires Python 3.10 or newer.

```sh
python3 app.py
```

The server listens at `http://127.0.0.1:8000` and creates `books.db` in the
current directory. Set `BOOKS_DB` to use another SQLite file or `PORT` to choose
another port.

## API

- `GET /health` returns `{"status": "ok"}`.
- `POST /books` creates a book and returns `201 Created`.
- `GET /books` lists all books; use `?author=Name` to return books by that exact author.
- `GET /books/{id}` returns a book or `404`.
- `PUT /books/{id}` replaces a book and returns it, or `404`.
- `DELETE /books/{id}` removes a book and returns `204 No Content`, or `404`.

Create and update requests must send JSON with non-empty `title` and `author`.
`year` is optional and must be an integer; `isbn` is optional and must be a string.

```sh
curl -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
```

## Test

```sh
python3 -m unittest -v
```
