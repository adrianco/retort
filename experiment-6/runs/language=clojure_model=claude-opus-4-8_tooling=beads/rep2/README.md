# Books API

A small REST API for managing a book collection, written in Clojure
(Ring + Jetty + Compojure) with data stored in an embedded **SQLite** database.

## Requirements

- Java 11+ (tested on a recent JDK)
- [Clojure CLI](https://clojure.org/guides/install_clojure) (`clojure` / `clj`)

Dependencies are declared in `deps.edn` and fetched automatically on first run.

## Run

```bash
clojure -M:run
```

The server starts on port `3000` and writes to `books.db` in the working
directory. Both are configurable via environment variables:

```bash
PORT=8080 DB_PATH=/tmp/books.db clojure -M:run
```

## Test

```bash
clojure -X:test
```

The test suite spins up the Ring handler against an in-memory SQLite database
and exercises every endpoint (health, create, validation, list/filter, get,
update, delete, 404 handling).

## API

All request and response bodies are JSON.

| Method | Path           | Description                                  | Success |
|--------|----------------|----------------------------------------------|---------|
| GET    | `/health`      | Health check                                 | 200     |
| POST   | `/books`       | Create a book                                | 201     |
| GET    | `/books`       | List books (optional `?author=` filter)      | 200     |
| GET    | `/books/{id}`  | Get a single book                            | 200     |
| PUT    | `/books/{id}`  | Update a book                                | 200     |
| DELETE | `/books/{id}`  | Delete a book                                | 204     |

### Book fields

| Field   | Type    | Required | Notes                |
|---------|---------|----------|----------------------|
| title   | string  | yes      | must be non-blank    |
| author  | string  | yes      | must be non-blank    |
| year    | integer | no       |                      |
| isbn    | string  | no       |                      |

`id` is assigned by the server.

### Status codes

- `400 Bad Request` — validation failed (response: `{"errors": [...]}`)
- `404 Not Found` — no book with the given id
- `204 No Content` — successful delete

## Examples

```bash
# Create
curl -XPOST localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"SICP","author":"Abelson","year":1985,"isbn":"0262011530"}'

# List, filtered by author
curl 'localhost:3000/books?author=Abelson'

# Get one
curl localhost:3000/books/1

# Update
curl -XPUT localhost:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"SICP, 2nd ed.","author":"Abelson","year":1996}'

# Delete
curl -XDELETE localhost:3000/books/1
```

## Project layout

```
deps.edn                  dependencies and aliases (:run, :test)
src/books/core.clj        entry point — starts Jetty
src/books/handler.clj     routing, validation, JSON middleware
src/books/db.clj          SQLite schema + CRUD
test/books/handler_test.clj  integration tests
```
