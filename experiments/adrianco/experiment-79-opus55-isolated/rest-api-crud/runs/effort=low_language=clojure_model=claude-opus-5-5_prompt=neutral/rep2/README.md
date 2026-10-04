# Books API

A small REST service for managing a book collection, written in Clojure with
Ring, Compojure and Jetty. Data is stored in a SQLite file via next.jdbc.

## Requirements

- Java 11+
- [Clojure CLI](https://clojure.org/guides/install_clojure)

## Run

```bash
clojure -M:run
```

The server listens on port 3000 and stores data in `books.db` in the current
directory. Both can be changed with environment variables:

```bash
PORT=8080 DB_PATH=/tmp/books.db clojure -M:run
```

## Test

```bash
clojure -M:test
```

Tests run the handler against a temporary SQLite file per test.

## API

A book is `{"id", "title", "author", "year", "isbn"}`. `title` and `author` are
required non-empty strings; `year` (integer) and `isbn` (string) are optional.

| Method | Path          | Description                              | Success | Errors   |
|--------|---------------|------------------------------------------|---------|----------|
| GET    | `/health`     | Health check                             | 200     |          |
| POST   | `/books`      | Create a book                            | 201     | 400      |
| GET    | `/books`      | List books; `?author=` filters by author | 200     |          |
| GET    | `/books/{id}` | Get one book                             | 200     | 404      |
| PUT    | `/books/{id}` | Replace a book (full body required)      | 200     | 400, 404 |
| DELETE | `/books/{id}` | Delete a book                            | 204     | 404      |

The author filter is an exact, case-insensitive match. Errors are returned as
`{"error": "...", "details": {...}}`, with `details` listing per-field
validation messages.

```bash
curl -X POST localhost:3000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'localhost:3000/books?author=Frank%20Herbert'
curl -X PUT localhost:3000/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:3000/books/1
```
