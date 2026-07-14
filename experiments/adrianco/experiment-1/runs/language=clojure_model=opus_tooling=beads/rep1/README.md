# Books REST API

A small Clojure REST API for managing a book collection, backed by SQLite.

## Requirements

- JDK 11+
- [Clojure CLI](https://clojure.org/guides/install_clojure) (`clojure` / `clj`)

## Run the server

```bash
clojure -M:run
```

By default the server listens on port `3000` and stores data in `books.db`
in the current directory. Override with environment variables:

```bash
PORT=8080 DB_PATH=/tmp/books.db clojure -M:run
```

## Run the tests

```bash
clojure -M:test
```

## Endpoints

| Method | Path              | Description                                        |
| ------ | ----------------- | -------------------------------------------------- |
| GET    | `/health`         | Health check, returns `{"status":"ok"}`            |
| POST   | `/books`          | Create a book (JSON body: title, author, year, isbn) |
| GET    | `/books`          | List all books; supports `?author=<name>` filter   |
| GET    | `/books/{id}`     | Get a single book                                  |
| PUT    | `/books/{id}`     | Update a book                                      |
| DELETE | `/books/{id}`     | Delete a book                                      |

`title` and `author` are required for both POST and PUT. Requests that
are missing them return HTTP 400 with a JSON error body.

## Example

```bash
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"1984","author":"Orwell","year":1949,"isbn":"978-0451524935"}'

curl http://localhost:3000/books
curl 'http://localhost:3000/books?author=Orwell'
curl http://localhost:3000/books/1
curl -X PUT http://localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"1984","author":"George Orwell","year":1949}'
curl -X DELETE http://localhost:3000/books/1
```

## Layout

- `src/books/core.clj` — Jetty entrypoint and middleware wiring
- `src/books/handler.clj` — Compojure routes, validation, JSON handling
- `src/books/db.clj` — SQLite access via `next.jdbc`
- `test/books/handler_test.clj` — integration tests using `ring.mock`
