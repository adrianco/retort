# Books REST API (Erlang)

A REST API service for managing a book collection, written in Erlang/OTP.

- **HTTP framework:** [Cowboy](https://github.com/ninenines/cowboy)
- **Storage:** DETS — Erlang's built-in embedded on-disk database (the
  language-equivalent of SQLite; no external database or NIF required).
  Data persists across restarts in a `.dets` file.
- **JSON:** OTP's built-in `json` module (OTP 27+).

## Requirements

- Erlang/OTP 27 or newer (tested on OTP 29)
- rebar3

## Setup and run

```sh
rebar3 compile        # fetch deps and build
rebar3 shell          # start the server (default port 8080)
```

The port and data file are configured in `config/sys.config`:

```erlang
[{books, [{port, 8080}, {data_file, "books.dets"}]}].
```

## Run the tests

```sh
rebar3 eunit
```

This runs unit tests for input validation plus integration tests that boot
the full application on port 8199 and exercise every endpoint over HTTP.

## API

| Method | Path                    | Description                            |
|--------|-------------------------|----------------------------------------|
| GET    | `/health`               | Health check → `{"status":"ok"}`       |
| POST   | `/books`                | Create a book → `201` + created book   |
| GET    | `/books`                | List all books (`?author=` to filter)  |
| GET    | `/books/{id}`           | Get one book → `200` or `404`          |
| PUT    | `/books/{id}`           | Replace a book → `200`, `400`, `404`   |
| DELETE | `/books/{id}`           | Delete a book → `204` or `404`         |

### Book fields

| Field    | Type    | Required                     |
|----------|---------|------------------------------|
| `title`  | string  | yes (non-empty, trimmed)     |
| `author` | string  | yes (non-empty, trimmed)     |
| `year`   | integer | no (`null` when omitted)     |
| `isbn`   | string  | no (`null` when omitted)     |

Validation failures return `400` with a JSON body such as
`{"errors":["title is required"]}`. Malformed JSON or a non-object body
also returns `400`. `PUT` is a full replacement, so `title` and `author`
are required there too.

### Examples

```sh
curl -X POST http://localhost:8080/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'
# {"id":1,"title":"Dune","author":"Frank Herbert","isbn":"978-0441172719","year":1965}

curl http://localhost:8080/books
curl 'http://localhost:8080/books?author=Frank%20Herbert'
curl http://localhost:8080/books/1

curl -X PUT http://localhost:8080/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'

curl -X DELETE http://localhost:8080/books/1   # 204 No Content
curl http://localhost:8080/health              # {"status":"ok"}
```

## Project layout

```
src/books_app.erl        application callback; starts the Cowboy listener
src/books_sup.erl        top-level supervisor
src/book_store.erl       gen_server wrapping the DETS table (CRUD + id counter)
src/books_handler.erl    HTTP handler for /books and /books/:id
src/books_validate.erl   input validation for book payloads
src/health_handler.erl   GET /health
test/books_validate_tests.erl  validation unit tests
test/books_api_tests.erl       full-stack HTTP integration tests
config/sys.config        runtime configuration (port, data file)
```
