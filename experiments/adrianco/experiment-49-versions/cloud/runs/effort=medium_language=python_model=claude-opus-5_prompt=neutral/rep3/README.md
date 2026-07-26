# Book Collection API

A small REST API for managing a book collection, built with **Flask** and **SQLite**
(via Python's stdlib `sqlite3`).

## Requirements

- Python 3.9+
- Flask (see `requirements.txt`)
- pytest, to run the tests

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The service listens on `http://127.0.0.1:5000` and creates `books.db` in the project
directory on first start. Two environment variables are honoured:

| Variable   | Default    | Meaning                     |
|------------|------------|-----------------------------|
| `PORT`     | `5000`     | Port to listen on           |
| `BOOKS_DB` | `books.db` | Path to the SQLite database |

For production use a WSGI server instead of the development server:

```bash
gunicorn 'app:create_app()'
```

## Tests

```bash
python -m pytest
```

The tests run against a temporary SQLite database per test (`tmp_path` fixture), so
they never touch your real `books.db`.

## API

A book is represented as:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" }
```

`title` and `author` are required non-empty strings. `year` (integer, -3000..2100) and
`isbn` (string) are optional and default to `null`.

| Method   | Path          | Description                             | Success        |
|----------|---------------|-----------------------------------------|----------------|
| `GET`    | `/health`     | Health check (also pings the DB)        | `200`          |
| `POST`   | `/books`      | Create a book                           | `201` + `Location` |
| `GET`    | `/books`      | List books, optional `?author=` filter  | `200`          |
| `GET`    | `/books/{id}` | Fetch one book                          | `200`          |
| `PUT`    | `/books/{id}` | Replace a book (full payload required)  | `200`          |
| `DELETE` | `/books/{id}` | Delete a book                           | `204`          |

The `?author=` filter is a case-insensitive **exact** match on the author name.

### Error responses

| Status | When                                                   | Body                                                |
|--------|--------------------------------------------------------|-----------------------------------------------------|
| `400`  | Missing/invalid fields, or a body that isn't JSON      | `{"error": "validation failed", "details": [...]}`  |
| `404`  | Unknown book id or unknown route                       | `{"error": "book not found"}`                       |
| `503`  | Database unreachable (health check only)               | `{"status": "error", "database": "unavailable"}`    |

All responses, including errors, are JSON.

### Examples

```bash
# Health
curl localhost:5000/health

# Create
curl -X POST localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

# List, and filter by author
curl localhost:5000/books
curl 'localhost:5000/books?author=Frank%20Herbert'

# Read, update, delete
curl localhost:5000/books/1
curl -X PUT localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -X DELETE localhost:5000/books/1
```

## Layout

```
app.py             # application factory, routes, validation
db.py              # SQLite connection handling and schema
tests/test_api.py  # integration tests exercising every endpoint
```
