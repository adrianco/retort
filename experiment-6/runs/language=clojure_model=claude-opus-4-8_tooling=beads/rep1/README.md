# Book Collection API

A small REST API for managing a book collection, written in Clojure
(Ring + Jetty + [reitit](https://github.com/metosin/reitit) routing,
[muuntaja](https://github.com/metosin/muuntaja) JSON negotiation, and
[next.jdbc](https://github.com/seancorfield/next-jdbc) over an embedded SQLite
database).

## Requirements

- Java 11+
- The [Clojure CLI](https://clojure.org/guides/install_clojure) (`clojure` / `deps.edn`)

All other dependencies are fetched automatically from Maven/Clojars on first run.

## Run

```bash
clojure -M:run
```

The server listens on port `3000` by default (override with the `PORT`
environment variable). Data is persisted to a `books.db` SQLite file created in
the working directory; the `books` table is created automatically on startup.

```bash
PORT=8080 clojure -M:run
```

## Test

```bash
clojure -X:test
```

The suite spins up the full Ring handler against a private in-memory SQLite
database and exercises every endpoint (health, create, validation, list/filter,
get, update, delete).

## API

All request and response bodies are JSON.

| Method | Path           | Description                                  |
|--------|----------------|----------------------------------------------|
| GET    | `/health`      | Liveness check → `{"status":"ok"}`           |
| POST   | `/books`       | Create a book                                |
| GET    | `/books`       | List all books (optional `?author=` filter)  |
| GET    | `/books/{id}`  | Fetch a single book                          |
| PUT    | `/books/{id}`  | Replace an existing book                     |
| DELETE | `/books/{id}`  | Delete a book                                |

### Book fields

| Field    | Type    | Required | Notes                     |
|----------|---------|----------|---------------------------|
| `title`  | string  | yes      |                           |
| `author` | string  | yes      |                           |
| `year`   | integer | no       | must be an integer if set |
| `isbn`   | string  | no       |                           |

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — validation failure or invalid id (body: `{"error": "..."}`)
- `404 Not Found` — book id does not exist

### Examples

```bash
# Health
curl localhost:3000/health

# Create
curl -X POST localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Herbert","year":1965,"isbn":"111"}'

# List, with optional author filter (case-insensitive)
curl localhost:3000/books
curl 'localhost:3000/books?author=Herbert'

# Get one
curl localhost:3000/books/1

# Update
curl -X PUT localhost:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"Dune Messiah","author":"Herbert","year":1969}'

# Delete
curl -X DELETE localhost:3000/books/1
```

## Project layout

```
deps.edn                  dependencies and run/test aliases
src/books/db.clj          SQLite persistence layer
src/books/handlers.clj    request handlers and input validation
src/books/core.clj        routing, middleware, server entry point
test/books/api_test.clj   end-to-end integration tests
```
