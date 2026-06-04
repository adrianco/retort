# Books API

A small REST API for managing a book collection, written in Clojure with
[Ring](https://github.com/ring-clojure/ring)/[Jetty](https://jetty.org/) and
[Compojure](https://github.com/weavejester/compojure), persisting data to an
embedded **SQLite** database via [next.jdbc](https://github.com/seancorfield/next-jdbc).

## Requirements

- JDK 11+ (tested on OpenJDK 26)
- [Clojure CLI](https://clojure.org/guides/install_clojure) (`clojure` / `clj`)

No `lein` required.

## Setup & Run

Dependencies are fetched automatically by the Clojure CLI on first run.

```bash
# Start the server (defaults: port 3000, SQLite file ./books.db)
clojure -M:run
```

Configuration via environment variables:

| Variable  | Default     | Description                                          |
|-----------|-------------|------------------------------------------------------|
| `PORT`    | `3000`      | HTTP port to listen on                               |
| `DB_PATH` | `books.db`  | SQLite file path. Use `:memory:` for an ephemeral DB |

```bash
PORT=8080 DB_PATH=/tmp/books.db clojure -M:run
```

## API

All request and response bodies are JSON. A book has the shape:

```json
{ "id": 1, "title": "SICP", "author": "Abelson", "year": 1985, "isbn": "0262011530" }
```

`title` and `author` are required on create/update; `year` and `isbn` are optional.

| Method   | Path             | Description                              | Status codes        |
|----------|------------------|------------------------------------------|---------------------|
| `GET`    | `/health`        | Health check                             | `200`               |
| `POST`   | `/books`         | Create a book                            | `201`, `400`        |
| `GET`    | `/books`         | List books (optional `?author=` filter)  | `200`               |
| `GET`    | `/books/{id}`    | Fetch one book                           | `200`, `400`, `404` |
| `PUT`    | `/books/{id}`    | Update a book                            | `200`, `400`, `404` |
| `DELETE` | `/books/{id}`    | Delete a book                            | `204`, `400`, `404` |

### Examples

```bash
# Health
curl localhost:3000/health

# Create
curl -X POST localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"SICP","author":"Abelson","year":1985,"isbn":"0262011530"}'

# List, with optional author filter
curl localhost:3000/books
curl 'localhost:3000/books?author=Abelson'

# Fetch / update / delete by id
curl localhost:3000/books/1
curl -X PUT localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"SICP 2e","author":"Abelson","year":1996}'
curl -X DELETE localhost:3000/books/1
```

Validation failures return `400` with a body such as:

```json
{ "errors": ["title is required", "author is required"] }
```

## Tests

Integration tests run the full Ring handler against an in-memory SQLite database:

```bash
clojure -X:test
```

## Project layout

```
deps.edn                     dependencies and aliases (:run, :test)
src/books/core.clj           entry point — wires DB + starts Jetty
src/books/handler.clj        routes, JSON encoding, validation
src/books/db.clj             SQLite persistence layer
test/books/handler_test.clj  integration tests
```
