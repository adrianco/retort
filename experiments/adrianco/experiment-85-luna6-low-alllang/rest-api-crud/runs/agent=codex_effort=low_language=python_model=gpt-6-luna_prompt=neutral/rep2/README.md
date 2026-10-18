# Book Collection API

A small JSON REST API for managing books. It uses Python's standard library and SQLite, so it has no third-party runtime dependencies.

## Requirements

- Python 3.10 or newer

## Run

From this directory, start the service with:

```sh
python app.py
```

The API listens on `http://127.0.0.1:8000` and stores data in `books.db` in the current directory. Set `BOOKS_HOST`, `BOOKS_PORT`, or `BOOKS_DATABASE` to configure the listener and database path.

## Endpoints

- `GET /health` — service health
- `POST /books` — create a book with JSON fields `title`, `author`, and optional `year`, `isbn`
- `GET /books` — list books; add `?author=Name` to filter (case insensitive)
- `GET /books/{id}` — retrieve one book
- `PUT /books/{id}` — replace a book's fields
- `DELETE /books/{id}` — delete a book

Create and update require non-empty `title` and `author`. `year` must be an integer when supplied; `isbn` must be a string when supplied. Missing books return `404`, invalid input returns `400`, creation returns `201`, and a successful deletion returns `204`.

Example:

```sh
curl -i -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl http://127.0.0.1:8000/books?author=Frank%20Herbert
```

## Tests

Run the integration and validation tests with:

```sh
python -m unittest -v
```
