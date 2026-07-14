# Books API

A small REST API for managing a book collection, written in Clojure
(Ring + Compojure + next.jdbc + SQLite).

## Requirements

- Java 11+
- [Clojure CLI](https://clojure.org/guides/install_clojure) (`clojure` /
  `clj`)

## Run the server

```sh
clojure -M:run
```

The server listens on port `3000` by default. Set the `PORT` environment
variable to override. Data is persisted in `books.db` in the working
directory.

## Run the tests

```sh
clojure -M:test
```

The tests use a temporary SQLite file per test run.

## Endpoints

| Method | Path           | Description                                |
| ------ | -------------- | ------------------------------------------ |
| GET    | `/health`      | Health check; returns `{"status":"ok"}`    |
| POST   | `/books`       | Create a book                              |
| GET    | `/books`       | List books (optional `?author=` filter)    |
| GET    | `/books/{id}`  | Fetch a single book                        |
| PUT    | `/books/{id}`  | Replace a book                             |
| DELETE | `/books/{id}`  | Delete a book                              |

### Book payload

```json
{
  "title":  "Dune",
  "author": "Frank Herbert",
  "year":   1965,
  "isbn":   "9780441172719"
}
```

`title` and `author` are required; `year` and `isbn` are optional. The
server responds with JSON and standard HTTP status codes (`201` on
create, `200` on read/update, `204` on delete, `400` on validation
failure, `404` when a book is not found).

### Examples

```sh
# create
curl -X POST http://localhost:3000/books \
     -H 'Content-Type: application/json' \
     -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

# list
curl http://localhost:3000/books
curl 'http://localhost:3000/books?author=Frank%20Herbert'

# fetch one
curl http://localhost:3000/books/1

# update
curl -X PUT http://localhost:3000/books/1 \
     -H 'Content-Type: application/json' \
     -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

# delete
curl -X DELETE http://localhost:3000/books/1
```

## Project layout

```
deps.edn                      Project + test dependencies
src/books/core.clj            Entry point: starts Jetty
src/books/db.clj              SQLite schema + CRUD
src/books/handler.clj         Ring/Compojure routes and validation
test/books/handler_test.clj   Integration tests
```
