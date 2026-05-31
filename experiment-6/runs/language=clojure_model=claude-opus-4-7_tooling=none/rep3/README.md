# Books REST API

A small REST API for managing a book collection, written in Clojure
using Ring + Jetty, Compojure, Cheshire, and SQLite (via next.jdbc).

## Requirements

- Java 11+
- [Clojure CLI tools](https://clojure.org/guides/install_clojure) (`clojure` / `clj`)

## Run

```bash
clojure -M:run
```

The server listens on port `3000` by default (override with `PORT=...`).
Data is persisted to `books.db` (SQLite) in the working directory.

## Test

```bash
clojure -M:test
```

Tests use an in-memory SQLite database, so they leave no files behind.

## API

| Method | Path           | Description                                |
|--------|----------------|--------------------------------------------|
| GET    | `/health`      | Health check — returns `{"status":"ok"}`   |
| GET    | `/books`       | List books. Supports `?author=` filter     |
| POST   | `/books`       | Create a book (title + author required)    |
| GET    | `/books/{id}`  | Fetch a single book                        |
| PUT    | `/books/{id}`  | Update a book                              |
| DELETE | `/books/{id}`  | Delete a book                              |

### Book schema

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441172719"
}
```

### Examples

```bash
# Create
curl -s -X POST localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

# List
curl -s localhost:3000/books
curl -s 'localhost:3000/books?author=Frank%20Herbert'

# Fetch / update / delete
curl -s localhost:3000/books/1
curl -s -X PUT localhost:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"Dune (revised)","author":"Frank Herbert","year":1965}'
curl -s -X DELETE localhost:3000/books/1
```

### Status codes

- `200 OK` — successful read / update
- `201 Created` — successful create
- `204 No Content` — successful delete
- `400 Bad Request` — validation error (missing title/author, bad year)
- `404 Not Found` — unknown id or route
