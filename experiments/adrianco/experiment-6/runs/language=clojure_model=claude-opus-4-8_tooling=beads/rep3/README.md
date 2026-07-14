# Books API

A small REST API for managing a book collection, written in Clojure.

- **HTTP / routing:** [Ring](https://github.com/ring-clojure/ring) + [reitit](https://github.com/metosin/reitit) on the Jetty adapter
- **JSON:** [muuntaja](https://github.com/metosin/muuntaja) (automatic request decoding / response encoding)
- **Storage:** SQLite via [next.jdbc](https://github.com/seancorfield/next-jdbc) and the `org.xerial/sqlite-jdbc` driver

## Requirements

- JDK 11+ (tested on JDK 26)
- [Clojure CLI](https://clojure.org/guides/install_clojure) (`clojure` / `clj`)

All other dependencies are fetched automatically from Maven/Clojars on first run.

## Run

```bash
# Start on the default port 3000 (creates ./books.db)
clojure -M:run

# Or choose a port
clojure -M:run 8080
```

The server prints `Starting books API on http://localhost:<port>` once it is up.
Book data is persisted to a `books.db` SQLite file in the working directory.

## Test

```bash
clojure -X:test
```

Tests run against a fresh in-memory SQLite database per test (no `books.db` file is created).

## API

All request and response bodies are JSON. Send `Content-Type: application/json`
on requests with a body.

| Method | Path           | Description                                    | Success status |
|--------|----------------|------------------------------------------------|----------------|
| GET    | `/health`      | Health check                                   | 200            |
| POST   | `/books`       | Create a book                                  | 201            |
| GET    | `/books`       | List all books (optional `?author=` filter)    | 200            |
| GET    | `/books/{id}`  | Get a single book                              | 200            |
| PUT    | `/books/{id}`  | Update a book                                  | 200            |
| DELETE | `/books/{id}`  | Delete a book                                  | 204            |

### Book fields

| Field    | Type    | Required |
|----------|---------|----------|
| `title`  | string  | yes      |
| `author` | string  | yes      |
| `year`   | integer | no       |
| `isbn`   | string  | no       |

### Status codes

- `200` / `201` / `204` — success
- `400` — validation failed (e.g. missing `title` or `author`); body contains an `errors` map
- `404` — book not found

### Examples

```bash
# Create
curl -X POST localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'
# -> 201 {"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}

# List all / filter by author
curl localhost:3000/books
curl 'localhost:3000/books?author=Frank%20Herbert'

# Get one
curl localhost:3000/books/1

# Update
curl -X PUT localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

# Delete
curl -X DELETE localhost:3000/books/1   # -> 204

# Validation error
curl -X POST localhost:3000/books \
  -H 'Content-Type: application/json' -d '{"year":2000}'
# -> 400 {"errors":{"title":"...","author":"..."}}
```

## Project layout

```
deps.edn                  # dependencies and aliases (:run, :test)
src/books/core.clj        # routes, app wiring, server entry point
src/books/handlers.clj    # Ring handlers
src/books/db.clj          # SQLite schema + CRUD queries
src/books/validation.clj  # request payload validation
test/books/api_test.clj   # integration tests
```
