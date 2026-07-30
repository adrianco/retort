# Book Collection API

A Flask REST API backed by SQLite.

## Setup and run

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

The service listens on `http://localhost:5000` and stores data in `books.db` by default. Set `BOOKS_DATABASE` to use a different SQLite database path.

## Endpoints

- `GET /health`
- `POST /books` with JSON: `title` and `author` (required), plus optional `year` and `isbn`
- `GET /books` (optional exact-match `?author=` filter)
- `GET /books/{id}`
- `PUT /books/{id}` with a complete valid book JSON body
- `DELETE /books/{id}`

Example:

```sh
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
```

## Tests

```sh
pytest -q
```
