# Book Collection API

A REST API for managing a book collection, built with
[Flask](https://flask.palletsprojects.com/) and SQLite.

## Setup

Requires Python 3.10 or newer.

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The API is then served at <http://127.0.0.1:8000>. The database file and its
table are created on first start. Settings come from environment variables:

| Variable        | Default             | Purpose                                   |
|-----------------|---------------------|-------------------------------------------|
| `PORT`          | `8000`              | Port to listen on                         |
| `HOST`          | `127.0.0.1`         | Interface to bind (`0.0.0.0` for all)     |
| `BOOKS_DB_PATH` | `instance/books.db` | SQLite database file                      |

For example: `PORT=9000 BOOKS_DB_PATH=/tmp/books.db python app.py`.

`python app.py` uses Flask's development server. In production, run the app
under a WSGI server instead, e.g. `pip install gunicorn` and then
`gunicorn "app:create_app()"`.

## API

| Method   | Path          | Success                                          | Errors         |
|----------|---------------|--------------------------------------------------|----------------|
| `GET`    | `/health`     | `200` `{"status": "ok", "database": "ok"}`       | `503`          |
| `POST`   | `/books`      | `201` the new book, plus a `Location` header     | `400`, `415`   |
| `GET`    | `/books`      | `200` array of books, ordered by id              |                |
| `GET`    | `/books/{id}` | `200` the book                                   | `404`          |
| `PUT`    | `/books/{id}` | `200` the updated book                           | `400`, `404`, `415` |
| `DELETE` | `/books/{id}` | `200` `{"id": 1, "deleted": true}`               | `404`          |

`GET /books?author=herbert` returns only the books whose author contains the
given text, ignoring case.

### Book fields

| Field    | Type            | Rules                                                          |
|----------|-----------------|----------------------------------------------------------------|
| `id`     | integer         | Assigned by the server; ignored if sent                        |
| `title`  | string          | **Required**, at most 500 characters, surrounding spaces trimmed |
| `author` | string          | **Required**, at most 500 characters, surrounding spaces trimmed |
| `year`   | integer or null | Optional, from 1 to the current year                           |
| `isbn`   | string or null  | Optional, a valid ISBN-10 or ISBN-13 (check digit verified); stored without hyphens or spaces |

Any other field is rejected. `PUT` replaces the whole book, so `title` and
`author` must be sent again, and an optional field that is left out is cleared.

### Errors

Every error response is JSON with an `error` message. Validation failures
(`400`) also list each invalid field under `details`:

```json
{"error": "Invalid book data", "details": {"title": "title is required"}}
```

Other status codes: `400` for a body that is not valid JSON, `404` for an
unknown book or route, `405` for an unsupported method, `413` for a body over
64 KB, and `415` when the `Content-Type` is not `application/json`.

### Examples

```bash
curl -i -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-17271-9"}'

curl http://127.0.0.1:8000/books
curl 'http://127.0.0.1:8000/books?author=herbert'
curl http://127.0.0.1:8000/books/1

curl -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "0-441-17271-7"}'

curl -X DELETE http://127.0.0.1:8000/books/1
curl http://127.0.0.1:8000/health
```

## Tests

```bash
python -m pytest
```

`tests/test_api.py` drives every endpoint through Flask's test client against
a temporary SQLite database; `tests/test_validation.py` unit-tests the input
rules.

## Project layout

```
app.py          Flask app factory, routes, JSON error handling, entry point
db.py           SQLite connection handling and queries
validation.py   Request payload validation
tests/          API and validation tests
```
