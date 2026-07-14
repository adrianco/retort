# books-api

A small REST API for managing a book collection, written in Rust with
[axum](https://docs.rs/axum) and SQLite (via the `rusqlite` `bundled` feature, so no
system SQLite library is required).

## Requirements

- Rust 1.75+ (any recent stable toolchain works)
- `cargo` on your `PATH`

## Build and run

```sh
cargo build --release
cargo run --release
```

By default the server listens on `0.0.0.0:3000` and stores its data in `books.db`
in the current directory. Both are configurable via environment variables:

```sh
BOOKS_ADDR=127.0.0.1:8080 BOOKS_DB=/tmp/books.db cargo run --release
```

## Run the tests

```sh
cargo test
```

The integration suite spins up the axum router against an in-memory SQLite database
and exercises every endpoint.

## Endpoints

| Method | Path           | Description                                |
|-------:|----------------|--------------------------------------------|
| GET    | `/health`      | Health check, returns `{"status":"ok"}`    |
| POST   | `/books`       | Create a book                              |
| GET    | `/books`       | List books, optional `?author=` filter     |
| GET    | `/books/{id}`  | Fetch a single book                        |
| PUT    | `/books/{id}`  | Replace a book                             |
| DELETE | `/books/{id}`  | Delete a book                              |

### Book payload

```json
{
  "title":  "The Rust Programming Language",
  "author": "Steve Klabnik",
  "year":   2019,
  "isbn":   "978-1718500440"
}
```

`title` and `author` are required; `year` and `isbn` are optional.

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST, body contains the created book (including `id`)
- `204 No Content` — successful DELETE
- `400 Bad Request` — missing `title` or `author`, or malformed JSON
- `404 Not Found` — no book with the given id

Error responses have the shape `{"error": "..."}`.

## Examples

```sh
# create
curl -s -X POST http://localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

# list, filter by author
curl -s 'http://localhost:3000/books?author=Frank%20Herbert'

# fetch by id
curl -s http://localhost:3000/books/1

# update
curl -s -X PUT http://localhost:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'

# delete
curl -s -X DELETE -o /dev/null -w '%{http_code}\n' http://localhost:3000/books/1
```

## Project layout

```
src/
  main.rs      — binary entrypoint, env-driven config
  lib.rs       — router wiring and shared state
  db.rs        — SQLite schema and CRUD helpers
  handlers.rs  — axum request handlers + validation
  models.rs    — request / response types
tests/
  integration.rs — end-to-end tests over the axum router
```
