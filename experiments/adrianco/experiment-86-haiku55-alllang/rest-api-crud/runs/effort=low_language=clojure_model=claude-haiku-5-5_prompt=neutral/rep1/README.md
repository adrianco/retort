# Books API

A REST API for managing a book collection, written in Clojure with Ring/Jetty and SQLite.

## Requirements

- Java 11+ (tested with OpenJDK 26)
- [Clojure CLI](https://clojure.org/guides/install_clojure) 1.11+

Dependencies are declared in `deps.edn` and downloaded automatically on first run.

## Run

```sh
clojure -M:run
```

Environment variables:

| Variable  | Default     | Description                    |
|-----------|-------------|--------------------------------|
| `PORT`    | `3000`      | HTTP port                      |
| `DB_PATH` | `books.db`  | Path to the SQLite database file (created if missing) |

Example:

```sh
PORT=8080 DB_PATH=./data/books.db clojure -M:run
```

## Test

```sh
clojure -M:test
```

The tests run the Ring handler in-process against a temporary SQLite file, so they need no running server.

## API

Books have the fields `id` (assigned by the server), `title` (required), `author` (required), `year` (optional integer), and `isbn` (optional string).

| Method   | Path          | Description                                 | Success |
|----------|---------------|---------------------------------------------|---------|
| `POST`   | `/books`      | Create a book                               | `201`   |
| `GET`    | `/books`      | List all books; `?author=` filters by author (case-insensitive exact match) | `200` |
| `GET`    | `/books/{id}` | Get one book                                | `200`   |
| `PUT`    | `/books/{id}` | Replace a book's fields (full update)       | `200`   |
| `DELETE` | `/books/{id}` | Delete a book                               | `204`   |
| `GET`    | `/health`     | Health check                                | `200`   |

`PUT` replaces the whole record, so omitting `year` or `isbn` clears them.

### Errors

All error responses are JSON of the form `{"error": "..."}`.

| Status | When                                                              |
|--------|-------------------------------------------------------------------|
| `400`  | Body is not valid JSON, or is not a JSON object                   |
| `404`  | No book with that id (or the path is not a valid id)              |
| `405`  | Method not supported on that path                                 |
| `422`  | Validation failed; `details` lists each problem                   |
| `500`  | Unexpected server error                                           |

Validation rules: `title` and `author` must be non-blank strings; `year` must be an integer when present; `isbn` must be a string when present.

## Examples

```sh
# Create
curl -i -X POST localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

# List, filtered by author
curl 'localhost:3000/books?author=Frank%20Herbert'

# Get
curl localhost:3000/books/1

# Update
curl -X PUT localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

# Delete
curl -i -X DELETE localhost:3000/books/1

# Health
curl localhost:3000/health
```

## Project layout

```
deps.edn                    Dependencies and aliases (:run, :test)
src/books/core.clj          Entry point; reads PORT and DB_PATH, starts Jetty
src/books/handler.clj       Routing, JSON parsing, validation, responses
src/books/db.clj            SQLite access via next.jdbc
test/books/api_test.clj     Integration tests through the Ring handler
test/books/runner.clj       Test runner used by `clojure -M:test`
```
