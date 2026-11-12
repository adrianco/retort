# Books API

A REST service for managing a book collection, written in Clojure
(Ring + Jetty + Compojure) with SQLite storage via next.jdbc.

## Requirements

- Java 11+
- [Clojure CLI](https://clojure.org/guides/install_clojure)

## Run

```bash
clojure -M:run
```

The server listens on port 3000 and stores data in `books.db`. Override with
the `PORT` and `DB_PATH` environment variables:

```bash
PORT=8080 DB_PATH=/tmp/books.db clojure -M:run
```

## Test

```bash
clojure -M:test
```

Tests run the full handler against a temporary SQLite database file.

## API

A book is `{"id": 1, "title": "...", "author": "...", "year": 1965, "isbn": "..."}`.
`title` and `author` are required non-empty strings; `year` (integer) and
`isbn` (string) are optional.

| Method | Path          | Description                              | Success | Errors   |
|--------|---------------|------------------------------------------|---------|----------|
| GET    | `/health`     | Health check                             | 200     |          |
| POST   | `/books`      | Create a book                            | 201     | 400      |
| GET    | `/books`      | List books; `?author=` filters exact match | 200   |          |
| GET    | `/books/{id}` | Get one book                             | 200     | 404      |
| PUT    | `/books/{id}` | Replace a book (full payload, validated) | 200     | 400, 404 |
| DELETE | `/books/{id}` | Delete a book                            | 204     | 404      |

Errors are JSON: `{"error": "Validation failed", "details": ["title is required ..."]}`.

## Example

```bash
curl -X POST localhost:3000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'localhost:3000/books?author=Frank%20Herbert'
curl -X DELETE localhost:3000/books/1
```

## Layout

- `src/books/core.clj` — routes, validation, server entry point
- `src/books/db.clj` — SQLite schema and queries
- `test/books/core_test.clj` — integration tests
