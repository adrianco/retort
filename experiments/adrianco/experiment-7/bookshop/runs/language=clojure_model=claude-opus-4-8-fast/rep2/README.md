# Book Collection API

A small REST API for managing a book collection, written in Clojure.

- **HTTP / routing:** Ring + Jetty + [reitit](https://github.com/metosin/reitit)
- **Persistence:** SQLite via [next.jdbc](https://github.com/seancorfield/next-jdbc) + HikariCP pool
- **JSON:** [Cheshire](https://github.com/dakrone/cheshire)

## Requirements

- Java 11+ (developed against OpenJDK 26)
- [Clojure CLI](https://clojure.org/guides/install_clojure) (`clojure` / `clj`)

All other dependencies are fetched automatically from Maven/Clojars on first run.

## Run

```bash
# Start on the default port 3000, storing data in ./books.db
clojure -M:run

# Or pick a port
clojure -M:run 8080
```

The SQLite database file (`books.db`) is created automatically on first start.

## Test

```bash
clojure -X:test
```

Tests run against an isolated in-memory SQLite database (one per test), so they
neither require nor touch the on-disk `books.db`.

## API

All request and response bodies are JSON.

| Method | Path           | Description                              |
|--------|----------------|------------------------------------------|
| GET    | `/health`      | Health check → `{"status":"ok"}`         |
| POST   | `/books`       | Create a book                            |
| GET    | `/books`       | List books; `?author=` filters by author |
| GET    | `/books/{id}`  | Fetch a single book                      |
| PUT    | `/books/{id}`  | Update a book                            |
| DELETE | `/books/{id}`  | Delete a book                            |

### Book fields

| Field    | Type    | Required | Notes                  |
|----------|---------|----------|------------------------|
| `title`  | string  | yes      |                        |
| `author` | string  | yes      |                        |
| `year`   | integer | no       |                        |
| `isbn`   | string  | no       |                        |

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — validation failure or invalid JSON (body: `{"errors":[...]}`)
- `404 Not Found` — unknown book id (body: `{"error":"book not found"}`)

## Examples

```bash
# Create
curl -X POST localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Herbert","year":1965,"isbn":"123"}'

# List all / filter by author
curl localhost:3000/books
curl 'localhost:3000/books?author=Herbert'

# Fetch one
curl localhost:3000/books/1

# Update
curl -X PUT localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Herbert","year":1969}'

# Delete
curl -X DELETE localhost:3000/books/1
```

## Project layout

```
deps.edn                  Dependencies and :run / :test aliases
src/books/core.clj        Server, routing, JSON middleware, entry point
src/books/handlers.clj    Request handlers and input validation
src/books/db.clj          SQLite access layer (next.jdbc)
test/books/api_test.clj   Integration tests (in-memory DB)
```
