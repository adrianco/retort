# Books REST API (Erlang / Cowboy)

A small REST service for managing a book collection.

## Stack

- **Language:** Erlang/OTP
- **HTTP:** [cowboy](https://github.com/ninenines/cowboy) 2.12
- **JSON:** [jsone](https://github.com/sile/jsone)
- **Storage:** `dets` — Erlang's built-in disk-based embedded key/value store (the language-equivalent of SQLite for this stack — no external native dependencies)

## Requirements

- Erlang/OTP 24 or newer (developed against OTP 29)
- [rebar3](https://rebar3.org/)

## Build

```sh
rebar3 compile
```

## Run

```sh
rebar3 shell
```

The server listens on port `8080` by default. Override with the `port` application env:

```sh
ERL_FLAGS="-books_app port 9000" rebar3 shell
```

Data is persisted to `books.dets` in the current working directory.

## Test

```sh
rebar3 eunit
```

The suite includes:
- `books_db_tests` — DB CRUD coverage (9 cases)
- `books_handler_tests` — input validation (6 cases)
- `books_api_tests` — full HTTP round-trip (7 cases)

## API

All responses are JSON. Bodies are persisted as-is plus a server-assigned `id`.

### `GET /health`

```
200 OK
{"status":"ok"}
```

### `POST /books`

Create a book. `title` and `author` are required and must be non-empty strings.

```sh
curl -s -X POST http://localhost:8080/books \
  -H 'content-type: application/json' \
  -d '{"title":"Programming Erlang","author":"Joe Armstrong","year":2013,"isbn":"978-1937785536"}'
```

Returns `201 Created` with the stored book (including the assigned `id`).
Returns `400 Bad Request` on invalid JSON or missing `title`/`author`.

### `GET /books`

List all books. Optional filter:

```sh
curl http://localhost:8080/books
curl 'http://localhost:8080/books?author=Joe%20Armstrong'
```

Returns `200 OK` with a JSON array.

### `GET /books/{id}`

```sh
curl http://localhost:8080/books/abc123...
```

Returns `200 OK` with the book, or `404 Not Found`.

### `PUT /books/{id}`

Partial update. Provided fields are merged onto the existing record; `title` and
`author` must remain non-empty after the merge.

```sh
curl -X PUT http://localhost:8080/books/abc123... \
  -H 'content-type: application/json' \
  -d '{"year":2014}'
```

Returns `200 OK` with the updated book, `400 Bad Request` on validation failure,
or `404 Not Found`.

### `DELETE /books/{id}`

```sh
curl -X DELETE http://localhost:8080/books/abc123...
```

Returns `204 No Content`, or `404 Not Found`.

## Project layout

```
rebar.config
src/
  books_app.app.src    OTP application descriptor
  books_app.erl        application callback — starts dets + cowboy
  books_sup.erl        top-level supervisor (no children yet, kept as scaffolding)
  books_db.erl         dets-backed CRUD
  books_handler.erl    /books and /books/:id cowboy handler
  books_health_handler.erl
test/
  books_db_tests.erl
  books_handler_tests.erl
  books_api_tests.erl  starts the live app and exercises every endpoint over HTTP
```
