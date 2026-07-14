# Books REST API

A small Clojure REST service for managing a book collection, backed by SQLite.

## Requirements

- JDK 11+ (tested on JDK 26)
- [Clojure CLI](https://clojure.org/guides/install_clojure) (`clj` / `clojure`)

All other dependencies are fetched automatically from Maven Central on first run.

## Running

```bash
clojure -M:run
```

The server listens on port `3000` by default and stores data in `./books.db`.
Both are configurable via environment variables:

```bash
PORT=8080 DB_PATH=/tmp/my-books.db clojure -M:run
```

## Tests

```bash
clojure -X:test
```

Tests use an isolated temporary SQLite file per fixture.

## Endpoints

| Method | Path           | Description                                    |
| ------ | -------------- | ---------------------------------------------- |
| GET    | `/health`      | Health check — returns `{"status":"ok"}`       |
| POST   | `/books`       | Create a book                                  |
| GET    | `/books`       | List all books (optional `?author=` filter)    |
| GET    | `/books/{id}`  | Fetch one book by id                           |
| PUT    | `/books/{id}`  | Replace fields on an existing book             |
| DELETE | `/books/{id}`  | Delete a book                                  |

### Book schema

```json
{
  "id": 1,
  "title": "Foundation",
  "author": "Isaac Asimov",
  "year": 1951,
  "isbn": "978-0553293357"
}
```

`title` and `author` are required on create and update. `year` (integer) and
`isbn` (string) are optional.

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — invalid JSON body or missing required field
- `404 Not Found` — book id does not exist

## Examples

```bash
# Create
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

# List, filtered
curl 'http://localhost:3000/books?author=Frank%20Herbert'

# Fetch one
curl http://localhost:3000/books/1

# Update
curl -X PUT http://localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (Deluxe Edition)","author":"Frank Herbert","year":1965}'

# Delete
curl -X DELETE http://localhost:3000/books/1
```

## Project layout

```
deps.edn                 — Clojure CLI deps and aliases
src/books/core.clj       — server bootstrap and routing
src/books/handlers.clj   — ring handlers + validation
src/books/db.clj         — SQLite schema and CRUD helpers
test/books/core_test.clj — integration tests through the ring handler
```
