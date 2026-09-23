# Books API

A REST API for managing a book collection, built with
[FastAPI](https://fastapi.tiangolo.com/) and stored in SQLite.

## Setup

Requires Python 3.10 or newer (tested with 3.10 through 3.14).

```bash
python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt     # to run the service
pip install -r requirements-dev.txt # to also run the tests
```

## Run

```bash
python -m books_api
```

The server listens on http://127.0.0.1:8000 and stores books in `./books.db`,
creating the file on first start. Interactive API docs are served at
http://127.0.0.1:8000/docs.

| Option   | Environment variable | Default     | Meaning                                           |
|----------|----------------------|-------------|---------------------------------------------------|
| `--host` | `BOOKS_API_HOST`     | `127.0.0.1` | Interface to listen on                            |
| `--port` | `BOOKS_API_PORT`     | `8000`      | Port to listen on                                 |
| `--db`   | `BOOKS_API_DB`       | `books.db`  | Path of the SQLite database file (not `:memory:`) |

An empty environment variable counts as unset. To accept connections from other
machines or containers, use for example
`python -m books_api --host 0.0.0.0 --port 8080 --db /data/books.db`. The API has
no authentication, so only do this on a network you trust.

The app is a standard ASGI application, so any ASGI server can host it,
for example `uvicorn books_api.app:app --workers 4` (set the database with
`BOOKS_API_DB`).

## API

| Method   | Path          | Success                                   | Errors        |
|----------|---------------|-------------------------------------------|---------------|
| `GET`    | `/health`     | `200` `{"status": "ok"}`                  | `503`         |
| `POST`   | `/books`      | `201` the new book, `Location` header     | `400`, `415`  |
| `GET`    | `/books`      | `200` array of books; `?author=` filters  |               |
| `GET`    | `/books/{id}` | `200` the book                            | `404`         |
| `PUT`    | `/books/{id}` | `200` the updated book                    | `400`, `404`, `415` |
| `DELETE` | `/books/{id}` | `204` no content                          | `404`         |

Any endpoint can also answer `413` to a request body over 1 MiB, and `503` when
the database cannot be used (for example, its file was deleted while the server ran).

A book looks like this:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}
```

| Field    | Rules                                                                    |
|----------|--------------------------------------------------------------------------|
| `id`     | Assigned by the server. Ignored if sent in a request body.               |
| `title`  | **Required.** String of 1–500 characters after trimming whitespace.      |
| `author` | **Required.** String of 1–500 characters after trimming whitespace.      |
| `year`   | Optional integer from 1 to the current year. Strings are not converted.  |
| `isbn`   | Optional string of up to 32 characters. An empty string is stored as `null`. |

Strings may not contain control characters, such as NUL, tab or newline, except as
leading or trailing whitespace, which is trimmed.

Behaviour worth knowing:

- **`PUT` replaces the whole book.** The body is validated exactly like `POST`, so
  `title` and `author` are required, and optional fields left out are cleared.
- **`?author=` matches part of the author's name, ignoring case**, including
  non-ASCII names: `?author=herbert` finds "Frank Herbert", and `?author=ÉMILE`
  finds "Émile Zola", however its accent was encoded. It is plain text, so `%`
  and `_` are not wildcards.
- `GET /books` returns books in the order they were added.
- An id that cannot exist, such as `/books/abc` or `/books/0`, returns `404` like any
  other unknown id. Ids of deleted books are never reused.
- Request bodies must be sent as `Content-Type: application/json`, or another
  `application/*+json` type. Anything else is `415`.

### Errors

Every error, including unknown routes (`404`) and unsupported methods (`405`,
with an `Allow` header), is returned as
[RFC 9457](https://www.rfc-editor.org/rfc/rfc9457) problem details with
`Content-Type: application/problem+json`. Validation failures list each invalid field:

```json
{
  "type": "about:blank",
  "title": "Bad Request",
  "status": 400,
  "detail": "Request validation failed",
  "errors": [{"field": "title", "message": "Field required"}]
}
```

### Examples

```bash
curl -i -X POST localhost:8000/books -H 'Content-Type: application/json' \
     -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}'

curl localhost:8000/books
curl 'localhost:8000/books?author=herbert'
curl localhost:8000/books/1

curl -X PUT localhost:8000/books/1 -H 'Content-Type: application/json' \
     -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965}'

curl -i -X DELETE localhost:8000/books/1
curl localhost:8000/health
```

## Tests

```bash
python -m pytest                               # run the test suite
python -m pytest --cov=books_api --cov-report=term-missing   # with coverage
```

- `tests/test_api.py` covers every endpoint over HTTP, using FastAPI's test
  client and a fresh SQLite file per test. It includes validation, status codes,
  error bodies and persistence across restarts.
- `tests/test_repository.py` tests the storage layer directly, including
  concurrent writers and a second process holding the database lock.
- `tests/test_server.py` starts the real server with `python -m books_api`, runs a
  full CRUD cycle over a socket, and checks the command-line options.

## Project layout

```
books_api/
  __main__.py   command-line entry point (python -m books_api)
  app.py        routes and the application factory, create_app()
  schemas.py    request and response models, with the validation rules
  db.py         SQLite repository
  errors.py     RFC 9457 error responses
tests/          pytest suite
```

Each database operation opens its own short-lived SQLite connection. This is safe
with FastAPI's thread pool, where a connection must not be shared between threads.
The database runs in WAL mode, so reads are not blocked while a write is in progress.
