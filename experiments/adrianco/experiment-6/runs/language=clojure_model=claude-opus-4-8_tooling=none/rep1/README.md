# Books API

A small REST API for managing a book collection, written in Clojure.

- **Web stack:** [Ring](https://github.com/ring-clojure/ring) + Jetty, [Compojure](https://github.com/weavejester/compojure) routing
- **JSON:** [Cheshire](https://github.com/dakrone/cheshire)
- **Storage:** embedded **SQLite** via [next.jdbc](https://github.com/seancorfield/next-jdbc)

## Requirements

- Java 11+ (tested on OpenJDK 26)
- [Clojure CLI](https://clojure.org/guides/install_clojure) (`clojure` / `clj`)

## Run

```bash
clojure -M:run
```

The server listens on **port 3000** by default and stores data in `books.db`.
Both are configurable via environment variables:

```bash
PORT=8080 DB_FILE=/var/data/books.db clojure -M:run
```

The SQLite schema is created automatically on startup.

## Test

```bash
clojure -X:test
```

Tests run against an in-memory SQLite database, so they leave no files behind.

## API

All request and response bodies are JSON. Send `Content-Type: application/json`
on requests with a body.

| Method | Path           | Description                                  |
|--------|----------------|----------------------------------------------|
| GET    | `/health`      | Health check — `{"status":"ok"}`             |
| POST   | `/books`       | Create a book                                |
| GET    | `/books`       | List books; optional `?author=` filter       |
| GET    | `/books/{id}`  | Get one book                                 |
| PUT    | `/books/{id}`  | Update a book                                |
| DELETE | `/books/{id}`  | Delete a book                                |

### Book shape

```json
{ "title": "SICP", "author": "Abelson", "year": 1985, "isbn": "0262011530" }
```

`title` and `author` are **required**; `year` and `isbn` are optional.

### Status codes

- `200` — successful GET / PUT
- `201` — book created
- `204` — book deleted (no body)
- `400` — validation failure or malformed/missing JSON body
- `404` — book (or route) not found

### Examples

```bash
# Create
curl -X POST localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"SICP","author":"Abelson","year":1985,"isbn":"0262011530"}'

# List all / filter by author
curl localhost:3000/books
curl "localhost:3000/books?author=Abelson"

# Get one
curl localhost:3000/books/1

# Update
curl -X PUT localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"SICP 2e","author":"Abelson","year":1996}'

# Delete
curl -X DELETE localhost:3000/books/1
```

## Project layout

```
src/books/core.clj      ; entry point — starts Jetty
src/books/handler.clj   ; routes, request handling, validation
src/books/db.clj        ; SQLite persistence
test/books/handler_test.clj
```
