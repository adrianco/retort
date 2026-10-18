# Books API

A REST API for managing a book collection, written in Clojure with Ring/Jetty and stored in SQLite.

## Requirements

- Java 17+ (tested with JDK 26)
- [Clojure CLI](https://clojure.org/guides/install_clojure) 1.11+

## Run

```sh
clojure -M -m books.core
```

Environment variables (optional):

| Variable  | Default     | Purpose                    |
|-----------|-------------|----------------------------|
| `PORT`    | `3000`      | HTTP port                  |
| `DB_PATH` | `books.db`  | SQLite database file path  |

The database file and its table are created automatically on first start.

## Test

```sh
clojure -M:test
```

## API

All bodies are JSON. Errors have the form `{"error": "...", "details": {...}}` (details only for validation errors).

| Method | Path          | Description                                   | Success |
|--------|---------------|-----------------------------------------------|---------|
| POST   | /books        | Create a book                                 | 201     |
| GET    | /books        | List books; optional `?author=` exact match   | 200     |
| GET    | /books/{id}   | Get one book                                  | 200     |
| PUT    | /books/{id}   | Replace a book's fields                       | 200     |
| DELETE | /books/{id}   | Delete a book                                 | 204     |
| GET    | /health       | Health check                                  | 200     |

Book fields: `title` (required, non-blank string), `author` (required, non-blank string),
`year` (optional integer), `isbn` (optional string). `id` is assigned by the server.

Invalid input returns `400`; unknown ids or routes return `404`; malformed JSON returns `400`.

### Examples

```sh
curl -s -X POST localhost:3000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl -s 'localhost:3000/books?author=Frank%20Herbert'
curl -s localhost:3000/books/1
curl -s -X PUT localhost:3000/books/1 -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -s -X DELETE localhost:3000/books/1 -o /dev/null -w '%{http_code}\n'
curl -s localhost:3000/health
```
