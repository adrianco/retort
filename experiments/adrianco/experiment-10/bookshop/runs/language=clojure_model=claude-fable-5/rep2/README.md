# Book API

A REST API for managing a book collection, written in Clojure with
[Ring](https://github.com/ring-clojure/ring) +
[Compojure](https://github.com/weavejester/compojure), backed by SQLite via
[next.jdbc](https://github.com/seancorfield/next-jdbc).

## Requirements

- Java (JDK 11+)
- [Clojure CLI](https://clojure.org/guides/install_clojure) (`clojure` / `clj`)

## Run the server

```sh
clojure -M:run
```

The server listens on `http://localhost:3000` and stores data in `books.db`
in the current directory. Both are configurable via environment variables:

```sh
PORT=8080 DB_PATH=/tmp/books.db clojure -M:run
```

## Run the tests

```sh
clojure -M:test
```

Tests run the full HTTP stack (via `ring-mock`) against a throwaway SQLite
database, covering the health check, CRUD operations, the author filter,
validation errors, and 404 handling.

## API

| Method | Path          | Description                                  |
|--------|---------------|----------------------------------------------|
| GET    | `/health`     | Health check — returns `{"status": "ok"}`    |
| POST   | `/books`      | Create a book                                 |
| GET    | `/books`      | List all books; filter with `?author=<name>` |
| GET    | `/books/{id}` | Get a single book                             |
| PUT    | `/books/{id}` | Update a book (full replace)                  |
| DELETE | `/books/{id}` | Delete a book                                 |

### Book fields

- `title` (string, **required**)
- `author` (string, **required**)
- `year` (integer, optional)
- `isbn` (string, optional)

### Status codes

- `200` — successful GET/PUT
- `201` — book created
- `204` — book deleted
- `400` — validation error or malformed JSON (`{"error": "..."}`)
- `404` — book (or route) not found

### Examples

```sh
# Health check
curl http://localhost:3000/health

# Create a book
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "SICP", "author": "Abelson & Sussman", "year": 1985, "isbn": "978-0262510875"}'

# List all books
curl http://localhost:3000/books

# Filter by author
curl 'http://localhost:3000/books?author=Abelson%20%26%20Sussman'

# Get one book
curl http://localhost:3000/books/1

# Update a book
curl -X PUT http://localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "SICP, 2nd ed.", "author": "Abelson & Sussman", "year": 1996}'

# Delete a book
curl -X DELETE http://localhost:3000/books/1
```

## Project layout

```
deps.edn                       Dependencies and run/test aliases
src/bookapi/core.clj           Entry point (Jetty server)
src/bookapi/handler.clj        Routes, JSON handling, validation
src/bookapi/db.clj             SQLite access (next.jdbc)
test/bookapi/handler_test.clj  Integration tests
```
