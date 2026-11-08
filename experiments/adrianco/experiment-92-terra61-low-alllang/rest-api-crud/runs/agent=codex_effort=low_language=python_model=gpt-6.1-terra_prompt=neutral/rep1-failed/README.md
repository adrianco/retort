# Book collection API

A Flask REST API backed by SQLite. Python 3.9 or newer is recommended.

## Setup and run

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The service listens on `http://127.0.0.1:5000`. It creates `books.sqlite3` in the current working directory on startup. Set `BOOKS_DATABASE` to use a different SQLite file path.

## API

All responses are JSON. A book has an integer `id`, string `title` and `author`, and optional `year` (integer or null) and `isbn` (string or null). Title and author must be non-empty strings. `PUT` replaces the book: both required fields must be provided, and omitted optional fields become null.

- `POST /books`: create a book; returns the book and HTTP 201.
- `GET /books`: list books; `?author=...` filters by exact author name.
- `GET /books/<id>`: fetch a book.
- `PUT /books/<id>`: replace a book.
- `DELETE /books/<id>`: delete a book.
- `GET /health`: returns `{"status": "ok"}`.

Invalid input returns HTTP 400 and an error object; missing books return HTTP 404.

Example:

```sh
curl -X POST http://127.0.0.1:5000/books -H 'Content-Type: application/json' -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'http://127.0.0.1:5000/books?author=Frank%20Herbert'
```

## Tests

```sh
pip install pytest
python -m pytest -q
```
