# Books API

A small REST service for managing a book collection, written in Clojure
(Ring + Compojure) with SQLite for storage.

## Requirements

- Java 11+ (tested on OpenJDK 26)
- [Clojure CLI](https://clojure.org/guides/install_clojure) (`clojure` / `clj`)

All other dependencies are declared in `deps.edn` and fetched automatically.

## Project layout

```
src/books/core.clj      ; entry point, starts the Jetty server
src/books/handler.clj   ; HTTP routes, validation, JSON responses
src/books/db.clj        ; SQLite persistence via next.jdbc
test/books/handler_test.clj
deps.edn
```

## Run

```bash
clojure -M:run            # starts on http://localhost:3000
clojure -M:run 8080       # or pass a port (also honors $PORT)
```

Data is persisted to a local `books.db` SQLite file, created on first run.

## Test

```bash
clojure -M:test
```

The tests use `ring-mock` against an isolated temporary SQLite database, so they
do not touch your `books.db` file.

## API

All request and response bodies are JSON.

| Method | Path           | Description                                  |
|--------|----------------|----------------------------------------------|
| GET    | `/health`      | Health check → `{"status":"ok"}`             |
| POST   | `/books`       | Create a book                                |
| GET    | `/books`       | List books, optional `?author=` filter       |
| GET    | `/books/{id}`  | Get a single book                            |
| PUT    | `/books/{id}`  | Update a book                                |
| DELETE | `/books/{id}`  | Delete a book                                |

A book has the fields: `title` (required), `author` (required), `year`, `isbn`.

### Status codes

- `200` — successful GET / PUT / DELETE
- `201` — book created
- `400` — validation failed (missing `title` or `author`)
- `404` — book not found

### Examples

```bash
# Create
curl -s -X POST localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"SICP","author":"Abelson","year":1985,"isbn":"0262011530"}'

# List (filtered)
curl -s 'localhost:3000/books?author=Abelson'

# Get one
curl -s localhost:3000/books/1

# Update
curl -s -X PUT localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"SICP (2nd ed.)","author":"Abelson","year":1996}'

# Delete
curl -s -X DELETE localhost:3000/books/1
```
