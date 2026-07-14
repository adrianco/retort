# Book Collection API

A REST API for managing a book collection, built with FastAPI and SQLite.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`. The SQLite database
file (`books.db`) is created automatically in the project root on startup.

Interactive API docs are available at `http://127.0.0.1:8000/docs`.

## Run tests

```bash
python3 -m pytest
```

## Endpoints

| Method | Path              | Description                          |
| ------ | ----------------- | ------------------------------------ |
| GET    | `/health`         | Health check                         |
| POST   | `/books`          | Create a book                        |
| GET    | `/books`          | List books (optional `?author=` filter) |
| GET    | `/books/{id}`     | Get a single book                    |
| PUT    | `/books/{id}`     | Update a book                        |
| DELETE | `/books/{id}`     | Delete a book                        |

### Book fields

- `title` (string, required)
- `author` (string, required)
- `year` (integer, optional)
- `isbn` (string, optional)

### Example requests

```bash
curl -X POST http://127.0.0.1:8000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}'

curl http://127.0.0.1:8000/books
curl "http://127.0.0.1:8000/books?author=Frank%20Herbert"
curl http://127.0.0.1:8000/books/1

curl -X PUT http://127.0.0.1:8000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}'

curl -X DELETE http://127.0.0.1:8000/books/1
```

### Status codes

- `201` on successful creation
- `200` on successful get/list/update
- `204` on successful delete
- `404` when a book id does not exist
- `422` when `title` or `author` is missing/empty
