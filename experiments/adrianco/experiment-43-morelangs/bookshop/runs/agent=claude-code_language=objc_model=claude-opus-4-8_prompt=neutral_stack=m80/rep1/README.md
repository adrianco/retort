# Book Collection API (Objective-C)

A small REST API for managing a book collection, written in Objective-C with
Foundation and backed by an embedded SQLite database. It ships its own minimal
HTTP/1.1 server (POSIX sockets + Grand Central Dispatch) — no third-party
frameworks required.

## Requirements

- macOS with the Command Line Tools (provides `clang`, Foundation, and
  `libsqlite3` — all included by default).

## Build & Run

```sh
make          # builds the ./bookapi binary
make run      # builds and starts the server on port 8080
```

Configuration (environment variables or first CLI argument):

| Setting  | Default    | How to set                          |
|----------|------------|-------------------------------------|
| Port     | `8080`     | `PORT=9000 ./bookapi` or `./bookapi 9000` |
| Database | `books.db` | `BOOKS_DB=/path/to/books.db ./bookapi`    |

The server binds to `127.0.0.1` and prints the address it is listening on. The
SQLite file is created automatically on first run.

```sh
./bookapi 8080
# Book API listening on http://127.0.0.1:8080  (db: books.db)
```

## API

All responses are JSON. Request bodies for `POST`/`PUT` are JSON objects.

| Method | Path            | Description                          | Success |
|--------|-----------------|--------------------------------------|---------|
| GET    | `/health`       | Health check                         | 200     |
| POST   | `/books`        | Create a book                        | 201     |
| GET    | `/books`        | List books (`?author=` filter)       | 200     |
| GET    | `/books/{id}`   | Fetch one book                       | 200     |
| PUT    | `/books/{id}`   | Update a book (partial, present keys)| 200     |
| DELETE | `/books/{id}`   | Delete a book                        | 204     |

### Book fields

- `title` — **required**, non-empty string
- `author` — **required**, non-empty string
- `year` — optional integer
- `isbn` — optional string
- `id` — assigned by the server

### Status codes

- `200 OK`, `201 Created`, `204 No Content` on success
- `400 Bad Request` — validation failure (missing `title`/`author`), malformed
  JSON, or an invalid `{id}`
- `404 Not Found` — unknown book id or unknown route
- `405 Method Not Allowed` — unsupported method on a known route

### Examples

```sh
# Create
curl -X POST http://127.0.0.1:8080/books \
  -d '{"title":"Dune","author":"Herbert","year":1965,"isbn":"9780441172719"}'
# -> 201 {"id":1,"title":"Dune","author":"Herbert","year":1965,"isbn":"9780441172719"}

# List, filtered by author (case-insensitive)
curl "http://127.0.0.1:8080/books?author=herbert"

# Fetch / update / delete
curl http://127.0.0.1:8080/books/1
curl -X PUT http://127.0.0.1:8080/books/1 -d '{"year":1966}'
curl -X DELETE http://127.0.0.1:8080/books/1   # -> 204

# Validation error
curl -X POST http://127.0.0.1:8080/books -d '{"author":"X"}'
# -> 400 {"error":"title is required"}
```

`PUT` is a partial update: only the JSON keys present in the request are
changed; omitted fields keep their existing values.

## Tests

```sh
make test
```

This builds and runs `run_tests`, which covers three layers:

1. **`BookStore`** — SQLite CRUD, validation, and the case-insensitive author
   filter, against an in-memory database.
2. **`Router`** — request-to-response mapping and status codes, exercised
   directly (no sockets).
3. **`HTTPServer`** — full end-to-end requests over a real loopback socket using
   `NSURLSession`, on an OS-assigned ephemeral port.

## Project layout

| File            | Responsibility                                      |
|-----------------|-----------------------------------------------------|
| `BookStore.{h,m}` | Thread-safe SQLite persistence and validation     |
| `Router.{h,m}`    | HTTP method/path → `BookStore` op, JSON + statuses |
| `HTTPServer.{h,m}`| Socket server, HTTP parsing, response writing      |
| `main.m`          | Wires the pieces together and runs the run loop    |
| `tests/tests.m`   | Unit + integration + end-to-end tests              |

The routing logic (`Router`) is deliberately decoupled from the networking
layer (`HTTPServer`) so it can be tested without opening sockets.
