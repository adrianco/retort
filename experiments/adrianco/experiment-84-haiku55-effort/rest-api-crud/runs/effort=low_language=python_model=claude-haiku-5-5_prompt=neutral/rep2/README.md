# Books API

A small REST API for managing a book collection. Built with the Python
standard library (`http.server` + `sqlite3`), so there are no runtime
dependencies.

## Requirements

- Python 3.10+ (tested with 3.13)

## Running

```sh
python books_api.py
```

The server listens on `http://127.0.0.1:8000` by default. Configure with
environment variables:

| Variable        | Default     | Purpose                          |
|-----------------|-------------|----------------------------------|
| `HOST`          | `127.0.0.1` | Interface to bind                |
| `PORT`          | `8000`      | Port to listen on                |
| `BOOKS_DB`      | `books.db`  | Path to the SQLite database file |
| `BOOKS_API_LOG` | unset       | Set to any value to log requests |

The database file and table are created automatically on first start.

## Running the tests

```sh
python -m unittest -v test_books_api.py
# or, with pytest installed:
python -m pytest -q test_books_api.py
```

## Endpoints

| Method | Path          | Description                            | Success                 |
|--------|---------------|----------------------------------------|-------------------------|
| POST   | `/books`      | Create a book                          | 201 + `Location` header |
| GET    | `/books`      | List books; optional `?author=` filter | 200                     |
| GET    | `/books/{id}` | Get one book                           | 200                     |
| PUT    | `/books/{id}` | Replace a book's fields                | 200                     |
| DELETE | `/books/{id}` | Delete a book                          | 204                     |
| GET    | `/health`     | Health check                           | 200                     |

### Book fields

| Field    | Type    | Required | Notes                    |
|----------|---------|----------|--------------------------|
| `title`  | string  | yes      | Non-empty after trimming |
| `author` | string  | yes      | Non-empty after trimming |
| `year`   | integer | no       | 0–9999                   |
| `isbn`   | string  | no       |                          |

`id` is assigned by the server. `PUT` replaces all editable fields, so
`title` and `author` must be supplied again; omitted `year`/`isbn` are
cleared to `null`.

The `author` filter matches the full author name, case-insensitively.

### Errors

Errors are JSON: `{"error": "..."}`. Validation failures (400) also include
`"details"` with a per-field message.

- `400` invalid JSON or failed validation
- `404` unknown path or book ID not found
- `405` method not supported on that path (includes `Allow` header)

## Examples

```sh
curl -i -X POST localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}'

curl 'localhost:8000/books?author=Frank%20Herbert'
curl -X PUT localhost:8000/books/1 -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965}'
curl -i -X DELETE localhost:8000/books/1
curl localhost:8000/health
```
