# Books REST API

A Clojure REST API for managing a book collection. Built with Ring + Jetty, Reitit routing, Muuntaja for JSON, and SQLite via next.jdbc.

## Requirements

- Clojure CLI (`clojure` / `clj`) 1.11+
- Java 11+

## Run

```bash
clojure -M:run
```

The server listens on port `3000` by default. Override with environment variables:

```bash
PORT=8080 DB_PATH=/tmp/books.db clojure -M:run
```

The SQLite database file is created on first run.

## Test

```bash
clojure -M:test
```

Each test runs against its own temporary SQLite database.

## Endpoints

| Method | Path                | Description                              |
| ------ | ------------------- | ---------------------------------------- |
| GET    | `/health`           | Health check                             |
| GET    | `/books`            | List all books. Optional `?author=` filter |
| POST   | `/books`            | Create a book                            |
| GET    | `/books/{id}`       | Get a book by id                         |
| PUT    | `/books/{id}`       | Update a book                            |
| DELETE | `/books/{id}`       | Delete a book                            |

### Book JSON shape

```json
{
  "id": 1,
  "title": "Clojure Programming",
  "author": "Chas Emerick",
  "year": 2012,
  "isbn": "978-1449394707"
}
```

`title` and `author` are required on POST and PUT; both must be non-blank strings.

### Status codes

- `200 OK` — successful GET or PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — validation error (missing/blank `title` or `author`, invalid id)
- `404 Not Found` — book not found / unknown route

## Example

```bash
# Create
curl -s -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"SICP","author":"Abelson","year":1985,"isbn":"978-0262510875"}'

# List, filter by author
curl -s 'http://localhost:3000/books?author=Abelson'

# Get one
curl -s http://localhost:3000/books/1

# Update
curl -s -X PUT http://localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"SICP (2nd Ed)","author":"Abelson","year":1996,"isbn":"978-0262510875"}'

# Delete
curl -s -X DELETE http://localhost:3000/books/1 -i
```

## Layout

```
deps.edn               # dependencies & aliases
src/books/core.clj     # entry point, Jetty bootstrap
src/books/routes.clj   # reitit router + middleware
src/books/handlers.clj # request handlers + validation
src/books/db.clj       # next.jdbc + SQLite access
test/books/core_test.clj
```
