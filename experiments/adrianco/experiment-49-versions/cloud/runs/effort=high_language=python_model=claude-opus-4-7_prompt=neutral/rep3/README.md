# Book Collection API

A minimal REST API for managing a book collection, built with Flask and SQLite.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The server listens on port `5000` by default (override with `PORT`). The SQLite
database file `books.db` is created in the project directory automatically
(override the location with `BOOKS_DB=/path/to/file.db`).

## Endpoints

| Method | Path              | Description                        |
| ------ | ----------------- | ---------------------------------- |
| GET    | `/health`         | Health check — returns `{"status":"ok"}` |
| POST   | `/books`          | Create a book                      |
| GET    | `/books`          | List books (optional `?author=` filter) |
| GET    | `/books/{id}`     | Get a book by id                   |
| PUT    | `/books/{id}`     | Replace a book                     |
| DELETE | `/books/{id}`    | Delete a book                      |

### Book payload

```json
{
  "title": "Dune",           // required, non-empty string
  "author": "Frank Herbert", // required, non-empty string
  "year": 1965,              // optional integer
  "isbn": "978-0441172719"   // optional string
}
```

### Example

```bash
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

curl http://localhost:5000/books?author=Frank%20Herbert
```

### Status codes

- `200` — successful GET / PUT
- `201` — book created
- `204` — book deleted
- `400` — invalid or missing fields (error details under `errors`)
- `404` — book not found

## Tests

```bash
pytest -q
```
