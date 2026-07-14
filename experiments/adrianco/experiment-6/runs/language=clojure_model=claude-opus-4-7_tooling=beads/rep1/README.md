# Books API

A small REST API for managing a book collection, written in Clojure on top of
Ring + Compojure + Jetty, with SQLite as the embedded store.

## Requirements

- Java 11+ (tested on Java 21)
- [Clojure CLI / `tools.deps`](https://clojure.org/guides/install_clojure) (1.11+)

No global SQLite install is needed; the `org.xerial/sqlite-jdbc` driver ships an
embedded native library.

## Run

```sh
clojure -M:run
```

The server listens on `http://localhost:3000` and stores data in `books.db` in
the current directory. Override with environment variables:

```sh
PORT=8080 DB_FILE=/tmp/my-books.db clojure -M:run
```

## Test

```sh
clojure -X:test
```

Tests use a fresh temporary SQLite file per test, so they don't touch your
development database.

## API

All bodies are JSON. Errors come back as `{"error": "..."}` or
`{"errors": ["..."]}` with an appropriate HTTP status.

| Method | Path                  | Description                              |
|--------|-----------------------|------------------------------------------|
| GET    | `/health`             | Health check — `{"status":"ok"}`         |
| GET    | `/books`              | List all books (optional `?author=`)     |
| GET    | `/books/{id}`         | Get a single book                        |
| POST   | `/books`              | Create a book                            |
| PUT    | `/books/{id}`         | Update a book                            |
| DELETE | `/books/{id}`         | Delete a book                            |

### Book shape

```json
{
  "id": 1,
  "title": "The Pragmatic Programmer",
  "author": "Andrew Hunt",
  "year": 1999,
  "isbn": "978-0201616224"
}
```

`title` and `author` are required on `POST` and `PUT`. `year` (integer) and
`isbn` (string) are optional.

### Examples

```sh
# Create
curl -sX POST localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Sapiens","author":"Yuval Noah Harari","year":2011,"isbn":"978-0062316097"}'

# List
curl -s localhost:3000/books
curl -s 'localhost:3000/books?author=Yuval%20Noah%20Harari'

# Get one
curl -s localhost:3000/books/1

# Update
curl -sX PUT localhost:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"Sapiens (revised)","author":"Yuval Noah Harari","year":2015}'

# Delete
curl -sX DELETE -i localhost:3000/books/1
```

### Status codes

- `200 OK` — successful read or update
- `201 Created` — successful create
- `204 No Content` — successful delete
- `400 Bad Request` — invalid id, malformed JSON, or failed validation
- `404 Not Found` — book id does not exist (or unknown route)

## Project layout

```
deps.edn                 — Clojure CLI dependencies and aliases
src/books/core.clj       — Entry point; configures and starts Jetty
src/books/handler.clj    — Compojure routes, validation, JSON middleware
src/books/db.clj         — SQLite schema and CRUD via next.jdbc
test/books/handler_test.clj — Integration tests against a temp SQLite DB
```
