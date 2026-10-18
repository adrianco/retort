# Book API

A REST API for managing a book collection, written in Clojure with Ring/Jetty and
stored in SQLite.

## Requirements

- Java 11+ (tested with OpenJDK 26)
- [Clojure CLI](https://clojure.org/guides/install_clojure) 1.11+

Dependencies are declared in `deps.edn` and downloaded automatically on first run.

## Run

```sh
clojure -M:run
```

The server listens on port `3000` and stores data in `books.db` in the current
directory. Override either with environment variables:

```sh
PORT=8080 DB_PATH=/tmp/books.db clojure -M:run
```

The database schema is created automatically on startup.

## Test

```sh
clojure -M:test
```

The suite contains integration tests that drive the HTTP handler against a real
temporary SQLite file, plus unit tests for validation.

## Endpoints

| Method | Path          | Description                                   |
|--------|---------------|-----------------------------------------------|
| POST   | `/books`      | Create a book. Returns `201` with the book.   |
| GET    | `/books`      | List all books. Supports `?author=` filter (case-insensitive exact match). |
| GET    | `/books/{id}` | Get one book. `200`, or `404` if missing.     |
| PUT    | `/books/{id}` | Replace a book's fields. `200`, or `404`.     |
| DELETE | `/books/{id}` | Delete a book. `204`, or `404`.               |
| GET    | `/health`     | Health check. Returns `{"status":"ok"}`.      |

### Book fields

| Field    | Type    | Required | Notes                          |
|----------|---------|----------|--------------------------------|
| `title`  | string  | yes      | Non-blank                      |
| `author` | string  | yes      | Non-blank                      |
| `year`   | integer | no       |                                |
| `isbn`   | string  | no       |                                |

`id` is assigned by the server. Strings are trimmed before storage.

### Status codes

- `400` — body is missing, not valid JSON, or not a JSON object
- `404` — book (or route) not found
- `405` — method not allowed on that path
- `422` — validation failed; response includes `fields` with per-field messages
- `500` — unexpected server error

## Examples

```sh
# Create
curl -i -X POST localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

# List, filtered by author
curl 'localhost:3000/books?author=Frank%20Herbert'

# Get, update, delete
curl localhost:3000/books/1
curl -X PUT localhost:3000/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -X DELETE localhost:3000/books/1

# Health
curl localhost:3000/health
```

## Project layout

```
deps.edn                     dependencies and aliases (:run, :test)
src/book_api/core.clj        entry point; starts Jetty
src/book_api/handler.clj     Ring handler and routing
src/book_api/db.clj          SQLite access via next.jdbc
src/book_api/validation.clj  input validation and normalization
test/book_api/               test namespaces and runner
```
