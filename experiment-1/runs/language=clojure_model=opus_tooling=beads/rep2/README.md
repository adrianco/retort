# Books REST API

A minimal Clojure REST API for managing a book collection. Uses Ring + Jetty + Compojure, with SQLite for storage via `next.jdbc`.

## Requirements

- [Clojure CLI tools](https://clojure.org/guides/install_clojure) (`clojure` / `clj`)
- Java 11+

## Setup

```bash
clojure -P          # pre-fetch dependencies
```

## Run

```bash
clojure -M:run
```

The server listens on port `3000` by default (override with `PORT`). SQLite data is stored in `books.db` (override with `DB_PATH`).

```bash
PORT=8080 DB_PATH=/tmp/books.db clojure -M:run
```

## Endpoints

| Method | Path           | Description                                   |
|--------|----------------|-----------------------------------------------|
| GET    | `/health`      | Health check                                  |
| POST   | `/books`       | Create a book (JSON body)                     |
| GET    | `/books`       | List books. Supports `?author=` filter        |
| GET    | `/books/{id}`  | Get a book by id                              |
| PUT    | `/books/{id}`  | Update a book (JSON body)                     |
| DELETE | `/books/{id}`  | Delete a book                                 |

Book fields: `title` (required), `author` (required), `year`, `isbn`.

### Example

```bash
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl http://localhost:3000/books?author=Frank%20Herbert
```

## Test

```bash
clojure -X:test
```

Tests cover create/get, validation, list/filter, update, delete, and 404 cases.
