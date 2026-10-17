# Book Collection API

A REST API for managing a book collection. It uses [Flask](https://flask.palletsprojects.com/) for HTTP and Python's built-in `sqlite3` module for storage.

## Requirements

- Python 3.10 or newer

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

`requirements.txt` lists the runtime dependency (Flask). `requirements-dev.txt` adds pytest.

## Run

```bash
python app.py
```

The server listens on `http://127.0.0.1:5000`. On macOS, port 5000 is often taken by AirPlay Receiver. To use another port, run `flask --app app run --port 5001` instead.

Books are stored in `books.db` in the current directory. To use a different file, set `BOOKS_DB_PATH`:

```bash
BOOKS_DB_PATH=/var/data/books.db python app.py
```

The `books` table is created on startup if it does not exist.

## API

| Method   | Path          | Purpose                          | Success                        | Errors                             |
|----------|---------------|----------------------------------|--------------------------------|------------------------------------|
| `GET`    | `/health`     | Liveness and database check      | `200`                          | `503` if the database is unreadable |
| `POST`   | `/books`      | Create a book                    | `201` with `Location` header   | `400`                              |
| `GET`    | `/books`      | List books; optional `?author=`  | `200`                          | `400`                              |
| `GET`    | `/books/{id}` | Get one book                     | `200`                          | `404`                              |
| `PUT`    | `/books/{id}` | Replace a book                   | `200`                          | `400`, `404`                       |
| `DELETE` | `/books/{id}` | Delete a book                    | `204`                          | `404`                              |

### Book fields

| Field    | Type    | Required | Rules                                                                                     |
|----------|---------|----------|-------------------------------------------------------------------------------------------|
| `title`  | string  | yes      | Not blank after trimming whitespace                                                       |
| `author` | string  | yes      | Not blank after trimming whitespace                                                       |
| `year`   | integer | no       | Between 1 and next calendar year                                                          |
| `isbn`   | string  | no       | ISBN-10 or ISBN-13. Hyphens and spaces are allowed. The check digit is not verified.      |

The server assigns `id` as an integer. A book looks like this:

```json
{"id": 1, "title": "Nineteen Eighty-Four", "author": "George Orwell", "year": 1949, "isbn": "978-0-451-52493-5"}
```

### Behavior notes

- **`PUT` replaces the whole book.** `title` and `author` are required on every update. Leaving out `year` or `isbn` clears that field.
- **Author filter.** `?author=` is a case-insensitive substring match, so `?author=orwell` matches `George Orwell`. A blank value returns `400`.
- **Duplicate ISBNs are allowed.** Two copies of the same book can share an ISBN.
- **Request bodies** must be JSON objects. The `Content-Type` header is optional.
- **Errors are JSON.** A validation failure returns `{"error": "Validation failed.", "details": {"<field>": "<message>"}}`. Other errors return `{"error": "<message>"}`.

## Examples

```bash
# Create
curl -i -X POST http://127.0.0.1:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Nineteen Eighty-Four", "author": "George Orwell", "year": 1949, "isbn": "978-0-451-52493-5"}'

# List, filtered by author
curl 'http://127.0.0.1:5000/books?author=orwell'

# Get one
curl http://127.0.0.1:5000/books/1

# Replace (title and author are required)
curl -X PUT http://127.0.0.1:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Nineteen Eighty-Four", "author": "George Orwell", "year": 1949}'

# Delete
curl -i -X DELETE http://127.0.0.1:5000/books/1
```

## Tests

```bash
pytest
```

Each test uses its own temporary SQLite file, so the tests never touch `books.db`.

## Project layout

| Path               | Contents                                                       |
|--------------------|----------------------------------------------------------------|
| `app.py`           | Flask app factory, routes, and error handling                  |
| `database.py`      | SQLite schema and queries                                      |
| `validation.py`    | Request validation rules                                       |
| `tests/`           | Endpoint tests through the test client, plus validation unit tests |
