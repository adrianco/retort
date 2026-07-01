# Book Collection API

A REST API for managing a book collection, built with FastAPI and SQLite.

## Requirements

- Python 3.9+

## Setup

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`. Interactive docs are at
`http://127.0.0.1:8000/docs`.

A SQLite database file (`books.db` by default) is created automatically on
startup in the working directory. Set the `BOOKS_DB_PATH` environment
variable to use a different location.

## API

| Method | Path                | Description                          |
|--------|---------------------|---------------------------------------|
| GET    | `/health`           | Health check                          |
| POST   | `/books`             | Create a book                         |
| GET    | `/books`             | List books (optional `?author=` filter) |
| GET    | `/books/{id}`        | Get a single book                     |
| PUT    | `/books/{id}`        | Update a book                         |
| DELETE | `/books/{id}`        | Delete a book                         |

### Book object

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441013593"
}
```

`title` and `author` are required (non-blank) on create and update. `year`
and `isbn` are optional.

### Example requests

```bash
curl -X POST http://127.0.0.1:8000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}'

curl "http://127.0.0.1:8000/books?author=Herbert"

curl http://127.0.0.1:8000/books/1

curl -X PUT http://127.0.0.1:8000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969, "isbn": "123"}'

curl -X DELETE http://127.0.0.1:8000/books/1
```

## Tests

```bash
pytest
```
