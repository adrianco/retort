# Books API

A small REST API for managing a book collection, written in Clojure
(Ring + Jetty + Compojure) with data stored in an embedded **SQLite** database
via `next.jdbc`.

## Requirements

- [Clojure CLI](https://clojure.org/guides/install_clojure) (tested with 1.12)
- JDK 11+ (tested with JDK 26)

All other dependencies are fetched automatically from Maven/Clojars on first run.

## Run

```bash
# Start the server on the default port (3000)
clojure -M:run

# ...or pick a port
clojure -M:run 8080
```

Data is persisted to `books.db` in the working directory (created on first run).

## Test

```bash
clojure -X:test
```

The suite uses an in-memory SQLite database and covers the health check,
creation + retrieval, validation, listing/filtering, update, delete, and
404 handling.

## API

All request and response bodies are JSON. Send `Content-Type: application/json`
on requests that include a body.

| Method | Path           | Description                              |
|--------|----------------|------------------------------------------|
| GET    | `/health`      | Health check → `{"status":"ok"}`         |
| POST   | `/books`       | Create a book                            |
| GET    | `/books`       | List books (optional `?author=` filter)  |
| GET    | `/books/{id}`  | Get a single book                        |
| PUT    | `/books/{id}`  | Update a book                            |
| DELETE | `/books/{id}`  | Delete a book                            |

A book looks like:

```json
{ "id": 1, "title": "Dune", "author": "Herbert", "year": 1965, "isbn": "99" }
```

`title` and `author` are required; `year` and `isbn` are optional.

### Status codes

- `200` — successful GET / PUT
- `201` — book created
- `204` — book deleted (no body)
- `400` — invalid JSON, missing required fields, or malformed id
- `404` — book not found / unknown route

### Examples

```bash
# Create
curl -H "Content-Type: application/json" -X POST localhost:3000/books \
  -d '{"title":"Dune","author":"Herbert","year":1965,"isbn":"99"}'

# List, filtered by author
curl "localhost:3000/books?author=Herbert"

# Get one
curl localhost:3000/books/1

# Update
curl -H "Content-Type: application/json" -X PUT localhost:3000/books/1 \
  -d '{"title":"Dune Messiah","author":"Herbert","year":1969}'

# Delete
curl -X DELETE localhost:3000/books/1
```

## Project layout

```
deps.edn                     # dependencies, :run and :test aliases
src/books/core.clj           # entry point — wires DB to the HTTP server
src/books/db.clj             # SQLite persistence layer
src/books/handler.clj        # routes, validation, JSON request/response
test/books/handler_test.clj  # integration tests over the full Ring app
```
