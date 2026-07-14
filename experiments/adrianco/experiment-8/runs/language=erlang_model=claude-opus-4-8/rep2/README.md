# booklib — Book Collection REST API

A small REST API for managing a book collection, written in **Erlang/OTP**.

It is intentionally **dependency-free** — it uses only the standard OTP
distribution:

- **HTTP server**: a minimal HTTP/1.1 server built on `gen_tcp`.
- **Storage**: `dets`, Erlang's built-in disk-based embedded database
  (the "language-equivalent embedded DB" in place of SQLite). Data persists in
  a `books.dets` file.
- **JSON**: the built-in `json` module (OTP 27+).

## Requirements

- Erlang/OTP **27 or newer** (developed and tested on OTP 29).
- [`rebar3`](https://rebar3.org) for building, running, and testing.

## Project layout

```
src/
  booklib.app.src     application metadata & config (port, db file)
  booklib_app.erl     application callback
  booklib_sup.erl     top-level supervisor (DB + HTTP server)
  booklib_db.erl      dets-backed storage + validation
  booklib_server.erl  TCP listener + acceptor pool
  booklib_http.erl    HTTP request parsing & response writing
  booklib_router.erl  request routing / dispatch
test/
  booklib_tests.erl   EUnit tests (storage layer + end-to-end HTTP)
```

## Build

```sh
rebar3 compile
```

## Run

Start the server (defaults to port **8080**):

```sh
rebar3 shell
```

The server boots automatically when the `booklib` application starts and logs
the port it is listening on. Press `Ctrl-C` twice to stop it.

### Changing the port

The port is read from the `booklib` application environment. Either edit
`{port, 8080}` in `src/booklib.app.src`, or set it at startup:

```sh
rebar3 shell --eval 'application:set_env(booklib, port, 9090).'
```

(A port of `0` asks the OS for an ephemeral port — handy for tests.)

## Test

```sh
rebar3 eunit
```

This runs 10 tests covering the storage/validation layer directly and the full
HTTP stack end-to-end (via `httpc`).

## API

All responses are JSON. Unless noted, request bodies must be JSON objects.

| Method | Path             | Description                                  |
|--------|------------------|----------------------------------------------|
| GET    | `/health`        | Health check                                 |
| POST   | `/books`         | Create a book                                |
| GET    | `/books`         | List books (optional `?author=` filter)      |
| GET    | `/books/{id}`    | Fetch a single book                          |
| PUT    | `/books/{id}`    | Replace a book                               |
| DELETE | `/books/{id}`    | Delete a book                                |

### Book fields

| Field    | Type            | Required | Notes                       |
|----------|-----------------|----------|-----------------------------|
| `title`  | string          | yes      | Must be non-empty           |
| `author` | string          | yes      | Must be non-empty           |
| `year`   | integer or null | no       | Defaults to `null`          |
| `isbn`   | string or null  | no       | Defaults to `null`          |
| `id`     | integer         | —        | Server-assigned, read-only  |

### Status codes

- `200 OK` — successful read/update/delete
- `201 Created` — book created
- `400 Bad Request` — malformed JSON or invalid id
- `404 Not Found` — unknown book or route
- `405 Method Not Allowed` — unsupported method on a known resource
- `422 Unprocessable Entity` — validation failed (details in `details`)

### Examples

```sh
# Health check
curl http://localhost:8080/health
# {"status":"ok"}

# Create a book
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'
# 201 {"author":"Frank Herbert","id":1,"isbn":"978-0441013593","title":"Dune","year":1965}

# List all books
curl http://localhost:8080/books
# {"books":[...],"count":1}

# Filter by author
curl 'http://localhost:8080/books?author=Frank%20Herbert'

# Fetch one
curl http://localhost:8080/books/1

# Update
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (Revised)","author":"Frank Herbert","year":1965}'

# Delete
curl -X DELETE http://localhost:8080/books/1
# {"deleted":1}

# Validation error
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' -d '{"author":"x"}'
# 422 {"error":"validation failed","details":["title is required"]}
```

## Notes

- The `?author=` filter is an exact, case-insensitive match.
- Data is persisted to `books.dets` in the working directory and survives
  restarts. Delete that file to reset the collection.
