# Book Collection API

A small REST service for managing a book collection, built with
[Flask](https://flask.palletsprojects.com/) and stored in SQLite (Python's
built-in `sqlite3`, so there is no database server to install).

## Setup

Requires Python 3.9 or newer.

```bash
python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt  # Flask + pytest; requirements.txt alone is enough to run
```

## Running

```bash
python -m bookapi
```

The API is now at <http://127.0.0.1:8000>. Try `curl http://127.0.0.1:8000/health`.
The database file is created on first start.

| Environment variable | Default    | Meaning                          |
|----------------------|------------|----------------------------------|
| `BOOKS_DB_PATH`      | `books.db` | SQLite file (relative to the working directory) |
| `HOST`               | `127.0.0.1`| Interface to listen on           |
| `PORT`               | `8000`     | Port to listen on                |

The default port is 8000, not Flask's usual 5000, because macOS uses port 5000 for AirPlay Receiver.

`python -m bookapi` uses Flask's development server. For production, run the
app factory under a WSGI server instead, for example:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 'bookapi:create_app()'
```

## API

All request and response bodies are JSON. Requests that carry a body (`POST`, `PUT`) must send
`Content-Type: application/json`.

| Method   | Path          | Description                                  | Success |
|----------|---------------|----------------------------------------------|---------|
| `GET`    | `/health`     | Health check that also reads the database    | `200` (`503` if the database is unusable) |
| `POST`   | `/books`      | Create a book                                | `201` + `Location` header |
| `GET`    | `/books`      | List all books (optional `?author=` filter)  | `200`   |
| `GET`    | `/books/{id}` | Get one book                                 | `200`   |
| `PUT`    | `/books/{id}` | Update (replace) a book                      | `200`   |
| `DELETE` | `/books/{id}` | Delete a book                                | `204`, empty body |

### The book resource

```json
{"id": 1, "title": "Nineteen Eighty-Four", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}
```

| Field    | Type            | Rules |
|----------|-----------------|-------|
| `id`     | integer         | Assigned by the server; never reused after a delete |
| `title`  | string          | **Required**, not blank, at most 500 characters |
| `author` | string          | **Required**, not blank, at most 255 characters |
| `year`   | integer or null | Optional; from 1 to next year (so forthcoming books can be added) |
| `isbn`   | string or null  | Optional; at most 32 characters. Stored exactly as given, without format checks |

Surrounding whitespace is trimmed from strings. Unknown fields are ignored.

### Behaviour worth knowing

- **Author filter**: `GET /books?author=orwell` returns books whose author *contains*
  the text, ignoring case (including non-ASCII letters: `garcía` matches `GARCÍA`).
  An empty filter returns every book. Books are listed in ID order.
- **`PUT` replaces the whole book.** Send `title` and `author`, as on create. A `year`
  or `isbn` left out of the request is cleared (set to `null`).
- An `id` that is not a positive integer (such as `/books/abc`) gets `404`, like a missing book.

### Examples

```bash
# Create a book
curl -i -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Nineteen Eighty-Four", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}'
# HTTP/1.1 201 CREATED
# Location: /books/1
# {"id":1,"title":"Nineteen Eighty-Four","author":"George Orwell","year":1949,"isbn":"978-0451524935"}

# List every book, or only George Orwell's
curl http://127.0.0.1:8000/books
curl 'http://127.0.0.1:8000/books?author=orwell'

# Get, replace and delete one book
curl http://127.0.0.1:8000/books/1
curl -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "1984", "author": "George Orwell", "year": 1949}'
curl -i -X DELETE http://127.0.0.1:8000/books/1   # HTTP/1.1 204 NO CONTENT
```

### Errors

Errors are JSON too, as `{"error": "<message>"}`. A validation failure also
reports every invalid field under `details`:

```bash
curl -X POST http://127.0.0.1:8000/books -H 'Content-Type: application/json' \
  -d '{"author": "", "year": "1949"}'
# HTTP/1.1 400 BAD REQUEST
# {"error":"Validation failed","details":{"title":"title is required","author":"author must not be blank","year":"year must be an integer"}}
```

| Status | When |
|--------|------|
| `400`  | Validation failed, or the body is not a JSON object (including malformed JSON) |
| `404`  | No book with that ID, or an unknown URL |
| `405`  | Method not supported on that URL (the `Allow` header lists the supported ones) |
| `413`  | Request body larger than 64 KiB |
| `415`  | Body sent without `Content-Type: application/json` |
| `500`  | Unexpected server error (details are logged, not returned) |
| `503`  | `GET /health` could not read the database (missing, corrupt or inaccessible) |

## Tests

```bash
python -m pytest
```

The suite is in `tests/`:

- `test_books_api.py`: integration tests of every endpoint, status code and error case, run through Flask's test client.
- `test_validation.py`: unit tests of the validation rules.
- `test_server.py`: end-to-end tests over real HTTP, against an in-process server and against `python -m bookapi` started as a subprocess.

Each test uses its own temporary SQLite file.

## Project layout

```
bookapi/
  __init__.py     create_app(): application factory and configuration
  __main__.py     `python -m bookapi` entry point
  routes.py       HTTP endpoints
  validation.py   payload validation and normalisation
  repository.py   SQL for the books table
  db.py           SQLite connections and schema
  errors.py       JSON error responses
tests/            pytest suite
```
