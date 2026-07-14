# Book Collection API

A small REST API for managing a book collection, written in Clojure.

Built with:
- **Ring** + **Jetty** — HTTP server
- **Compojure** — routing
- **next.jdbc** + **SQLite** (xerial JDBC driver) — embedded persistence
- **Cheshire** — JSON serialization

## Requirements

- Java 11+
- [Clojure CLI](https://clojure.org/guides/install_clojure) (`clojure` / `clj`)

## Run

```bash
clojure -M:run
```

The server starts on port `3000` by default. Override with the `PORT`
environment variable:

```bash
PORT=8080 clojure -M:run
```

Data is stored in a local SQLite file, `books.db`, created automatically on
first run.

## Test

```bash
clojure -M:test
```

Tests run against an in-memory SQLite database, so they leave no files behind.

## API

All request and response bodies are JSON. Send `Content-Type: application/json`
on requests that include a body.

| Method | Path           | Description                              |
|--------|----------------|------------------------------------------|
| GET    | `/health`      | Health check                             |
| POST   | `/books`       | Create a book                            |
| GET    | `/books`       | List all books (`?author=` filter)       |
| GET    | `/books/{id}`  | Get a single book                        |
| PUT    | `/books/{id}`  | Update a book                            |
| DELETE | `/books/{id}`  | Delete a book                            |

A book has the fields: `title` (required), `author` (required), `year`, `isbn`.

### Examples

```bash
# Health check
curl localhost:3000/health
# => {"status":"ok"}

# Create a book
curl -H "Content-Type: application/json" -X POST localhost:3000/books \
  -d '{"title":"Dune","author":"Herbert","year":1965,"isbn":"111"}'
# => {"id":1,"title":"Dune","author":"Herbert","year":1965,"isbn":"111"}

# List all books
curl localhost:3000/books

# Filter by author
curl "localhost:3000/books?author=Herbert"

# Get one book
curl localhost:3000/books/1

# Update a book
curl -H "Content-Type: application/json" -X PUT localhost:3000/books/1 \
  -d '{"title":"Dune Messiah","author":"Herbert","year":1969}'

# Delete a book
curl -X DELETE localhost:3000/books/1
```

### Status codes

- `200 OK` — successful read / update / delete
- `201 Created` — book created
- `400 Bad Request` — invalid JSON or missing required fields
  (`title`/`author`)
- `404 Not Found` — book id does not exist

## Project layout

```
deps.edn                      project + dependencies
src/books/core.clj            entry point — wires DB and starts Jetty
src/books/db.clj              SQLite persistence layer
src/books/handler.clj         routes, validation, JSON responses
test/books/handler_test.clj   integration tests
```
