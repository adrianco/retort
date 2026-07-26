# Book Collection REST API

A small REST API for managing a book collection, built with Flask and SQLite.

## Requirements

- Python 3.9+
- `pip`

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running

```bash
python app.py
```

The server listens on `http://localhost:5000` by default. Override with the
`PORT` environment variable. The SQLite database file is `books.db` in the
current directory, overridable with the `DATABASE` environment variable.

## Endpoints

| Method | Path             | Description                                   |
|--------|------------------|-----------------------------------------------|
| GET    | `/health`        | Health check — `{"status": "ok"}`             |
| POST   | `/books`         | Create a book (JSON body)                     |
| GET    | `/books`         | List books; supports `?author=` filter        |
| GET    | `/books/{id}`    | Fetch a single book                           |
| PUT    | `/books/{id}`    | Update a book (partial fields allowed)        |
| DELETE | `/books/{id}`    | Delete a book                                 |

### Book payload

```json
{
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441172719"
}
```

`title` and `author` are required on creation and must be non-empty strings.
`year` (integer) and `isbn` (string) are optional.

### Example

```bash
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

curl 'http://localhost:5000/books?author=Frank%20Herbert'
```

## Status codes

- `200 OK` — successful GET/PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — invalid or missing fields
- `404 Not Found` — unknown book id or route

## Tests

```bash
pytest -v
```
