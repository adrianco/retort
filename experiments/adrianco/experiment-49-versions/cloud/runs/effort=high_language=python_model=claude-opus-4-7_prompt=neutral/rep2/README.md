# Books REST API

A small Flask + SQLite REST service for managing a book collection.

## Requirements

- Python 3.10+
- `pip`

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python3 app.py
```

The service listens on `http://127.0.0.1:5000` by default. Override the port
with `PORT=8080 python3 app.py` and the SQLite file location with
`DATABASE_URL=/path/to/books.db python3 app.py`. If unset, the database file
`books.db` is created next to `app.py` on first start.

## Endpoints

| Method | Path             | Description                                    |
| ------ | ---------------- | ---------------------------------------------- |
| GET    | `/health`        | Liveness / DB check                            |
| POST   | `/books`         | Create a book                                  |
| GET    | `/books`         | List all books (optional `?author=` filter)    |
| GET    | `/books/{id}`    | Fetch a book by id                             |
| PUT    | `/books/{id}`    | Update a book (partial updates allowed)        |
| DELETE | `/books/{id}`    | Delete a book                                  |

### Book schema

```json
{
  "id": 1,
  "title": "The Pragmatic Programmer",
  "author": "Andy Hunt",
  "year": 1999,
  "isbn": "978-0201616224"
}
```

`title` and `author` are required non-empty strings. `year` (integer) and
`isbn` (string) are optional.

### Example

```bash
curl -X POST http://127.0.0.1:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'

curl http://127.0.0.1:5000/books
curl 'http://127.0.0.1:5000/books?author=Frank%20Herbert'
curl http://127.0.0.1:5000/books/1
curl -X PUT http://127.0.0.1:5000/books/1 \
  -H 'Content-Type: application/json' -d '{"year":1966}'
curl -X DELETE http://127.0.0.1:5000/books/1
```

## Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — validation failure or malformed JSON
- `404 Not Found` — unknown book id or route
- `405 Method Not Allowed` — wrong verb for a known route

## Tests

```bash
python3 -m pytest -v
```

18 tests cover the health endpoint, CRUD paths, validation, filtering, and
error responses. Each test uses a fresh temporary SQLite file so runs are
isolated.
