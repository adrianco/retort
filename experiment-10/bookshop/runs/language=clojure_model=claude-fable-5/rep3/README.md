# Book API

A REST API for managing a book collection, written in Clojure with Ring/Compojure and SQLite.

## Requirements

- Java 11+
- [Clojure CLI](https://clojure.org/guides/install_clojure) (`clojure` / `clj`)

## Run

```sh
clojure -M:run
```

The server listens on `http://localhost:3000` by default and stores data in `books.db`
in the working directory. Both are configurable via environment variables:

```sh
PORT=8080 DB_PATH=/tmp/books.db clojure -M:run
```

## Test

```sh
clojure -M:test
```

## API

| Method | Path          | Description                                  |
|--------|---------------|----------------------------------------------|
| GET    | `/health`     | Health check — returns `{"status": "ok"}`    |
| POST   | `/books`      | Create a book — returns 201 with the book    |
| GET    | `/books`      | List all books; supports `?author=` filter   |
| GET    | `/books/{id}` | Get a book by id — 404 if not found          |
| PUT    | `/books/{id}` | Update a book — 404 if not found             |
| DELETE | `/books/{id}` | Delete a book — 204 on success, 404 if absent|

A book has the fields `title` (required), `author` (required), `year` (optional integer),
and `isbn` (optional string). Validation failures return 400 with an `errors` array.

### Examples

```sh
# Create
curl -s -X POST localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "SICP", "author": "Abelson", "year": 1985, "isbn": "0-262-01077-1"}'

# List (optionally filtered by author)
curl -s 'localhost:3000/books?author=Abelson'

# Get one
curl -s localhost:3000/books/1

# Update
curl -s -X PUT localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "SICP 2nd ed", "author": "Abelson", "year": 1996, "isbn": "0-262-01153-0"}'

# Delete
curl -s -X DELETE localhost:3000/books/1 -i
```

## Project layout

```
deps.edn                      Dependencies and run/test aliases
src/bookapi/core.clj          Entry point (Jetty server)
src/bookapi/handler.clj       Routes, validation, JSON middleware
src/bookapi/db.clj            SQLite access via next.jdbc
test/bookapi/handler_test.clj Integration tests against the Ring handler
```
