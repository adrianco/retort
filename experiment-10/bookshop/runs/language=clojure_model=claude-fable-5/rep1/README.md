# Book API

A REST API for managing a book collection, written in Clojure with
[Ring](https://github.com/ring-clojure/ring) + [Compojure](https://github.com/weavejester/compojure),
backed by SQLite via [next.jdbc](https://github.com/seancorfield/next-jdbc).

## Requirements

- Java 11+ (JDK)
- [Clojure CLI](https://clojure.org/guides/install_clojure) (`clojure` / `clj`)

## Run

```sh
clojure -M:run
```

The server listens on `http://localhost:3000` and stores data in `books.db`
in the working directory. Both are configurable via environment variables:

```sh
PORT=8080 DB_PATH=/tmp/books.db clojure -M:run
```

## Test

```sh
clojure -M:test
```

Tests run the full Ring handler against a temporary SQLite database and cover
the health check, CRUD operations, validation errors, the author filter, and
404 handling.

## API

| Method | Path          | Description                                |
|--------|---------------|--------------------------------------------|
| GET    | `/health`     | Health check                               |
| POST   | `/books`      | Create a book                              |
| GET    | `/books`      | List all books; supports `?author=` filter |
| GET    | `/books/{id}` | Get a book by ID                           |
| PUT    | `/books/{id}` | Update a book (full replacement)           |
| DELETE | `/books/{id}` | Delete a book                              |

A book has the fields `title` (string, required), `author` (string, required),
`year` (integer, optional), and `isbn` (string, optional). Validation failures
return `400` with an `errors` array; unknown IDs return `404`.

### Examples

```sh
# Create
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"SICP","author":"Abelson","year":1996,"isbn":"978-0262510875"}'
# => 201 {"id":1,"title":"SICP","author":"Abelson","year":1996,"isbn":"978-0262510875"}

# List / filter
curl http://localhost:3000/books
curl 'http://localhost:3000/books?author=Abelson'

# Get one
curl http://localhost:3000/books/1

# Update
curl -X PUT http://localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"SICP, 2nd ed.","author":"Abelson and Sussman","year":1996}'

# Delete (returns 204)
curl -X DELETE http://localhost:3000/books/1
```

## Project layout

```
deps.edn                      dependencies and run/test aliases
src/bookapi/core.clj          entrypoint: starts Jetty
src/bookapi/handler.clj       routes, validation, JSON middleware
src/bookapi/db.clj            SQLite persistence (next.jdbc)
test/bookapi/handler_test.clj integration tests against the Ring handler
```
