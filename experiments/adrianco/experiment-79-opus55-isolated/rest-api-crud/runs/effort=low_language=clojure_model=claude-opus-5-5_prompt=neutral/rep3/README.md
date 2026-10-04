# Books API

A REST API for managing a book collection, written in Clojure with Ring,
Compojure and SQLite (via next.jdbc).

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

Tests run the full Ring handler against a temporary SQLite file per test.

## API

| Method | Path          | Description                          | Success |
|--------|---------------|--------------------------------------|---------|
| GET    | `/health`     | Health check                         | 200     |
| POST   | `/books`      | Create a book                        | 201     |
| GET    | `/books`      | List books (optional `?author=`)     | 200     |
| GET    | `/books/{id}` | Get one book                         | 200     |
| PUT    | `/books/{id}` | Replace a book                       | 200     |
| DELETE | `/books/{id}` | Delete a book                        | 204     |

A book is `{"id", "title", "author", "year", "isbn"}`. `title` and `author`
are required non-empty strings; `year` (integer) and `isbn` (string) are
optional. `PUT` replaces the whole book, so omitted optional fields become null.
The `author` filter is an exact match.

Errors are JSON: `400` for invalid JSON or failed validation
(`{"error": "...", "details": [...]}`), `404` for an unknown book or route.

```bash
curl -X POST localhost:3000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'localhost:3000/books?author=Frank%20Herbert'
```
