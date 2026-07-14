# Books REST API (Clojure)

A small REST API for managing a book collection. Built with Ring + Jetty,
Compojure routing, and SQLite (via `next.jdbc` and `org.xerial/sqlite-jdbc`).

## Requirements

- Java 11+
- [Clojure CLI](https://clojure.org/guides/install_clojure) (`clojure` /
  `deps.edn` tooling)

## Run

```sh
clojure -M:run
```

The server listens on `http://localhost:3000` and persists data to
`books.db` in the working directory. Override with environment variables:

```sh
PORT=8080 DB_PATH=/tmp/books.db clojure -M:run
```

## Test

```sh
clojure -M:test
```

Tests use an in-memory SQLite database, so they leave no files behind.

## Endpoints

| Method | Path           | Description                                  |
| ------ | -------------- | -------------------------------------------- |
| GET    | `/health`      | Liveness probe; returns `{"status":"ok"}`    |
| POST   | `/books`       | Create a book (`title`, `author` required)   |
| GET    | `/books`       | List books; optional `?author=` filter       |
| GET    | `/books/{id}`  | Fetch one book                               |
| PUT    | `/books/{id}`  | Partial update (any subset of fields)        |
| DELETE | `/books/{id}`  | Delete a book                                |

### Book payload

```json
{
  "title":  "Dune",
  "author": "Frank Herbert",
  "year":   1965,
  "isbn":   "9780441172719"
}
```

### Status codes

- `200 OK` — successful GET/PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — validation failure (missing/blank `title` or `author`,
  non-integer `year`, malformed id)
- `404 Not Found` — unknown book id or route

### Examples

```sh
curl -s -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

curl -s http://localhost:3000/books
curl -s 'http://localhost:3000/books?author=Frank%20Herbert'
curl -s http://localhost:3000/books/1

curl -s -X PUT http://localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":1966}'

curl -s -X DELETE http://localhost:3000/books/1 -i
```
