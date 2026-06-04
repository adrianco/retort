# booksapp — Book Collection REST API

A small REST API for managing a book collection, written in Erlang/OTP
using the [Cowboy](https://github.com/ninenines/cowboy) HTTP server.

- **HTTP framework:** Cowboy 2.12
- **JSON:** the built-in `json` module (Erlang/OTP 27+)
- **Storage:** `dets` — Erlang/OTP's built-in disk-based embedded database
  (the language-equivalent of SQLite). Data persists to `books.dets` in the
  working directory.

## Requirements

- Erlang/OTP 27 or newer (tested on OTP 29)
- [rebar3](https://rebar3.org/)

## Setup & Run

```sh
# Fetch dependencies and compile
rebar3 compile

# Start the server (listens on port 8080 by default)
rebar3 shell
```

The listener port can be configured via the `port` application environment,
e.g. by editing `src/booksapp.app.src` or setting it before start.

Once running, the API is available at `http://localhost:8080`.

## API

All request and response bodies are JSON.

| Method | Path                     | Description                              | Success |
|--------|--------------------------|------------------------------------------|---------|
| GET    | `/health`                | Liveness check                           | 200     |
| POST   | `/books`                 | Create a book                            | 201     |
| GET    | `/books`                 | List books (optional `?author=` filter)  | 200     |
| GET    | `/books/{id}`            | Get a single book                        | 200     |
| PUT    | `/books/{id}`            | Update a book                            | 200     |
| DELETE | `/books/{id}`            | Delete a book                            | 204     |

A book has the fields: `id` (assigned by the server), `title`, `author`,
`year`, `isbn`. **`title` and `author` are required** on create; an invalid
or missing value yields `400` with an `{"error": "..."}` body. Unknown IDs
yield `404`.

### Examples

```sh
# Health check
curl http://localhost:8080/health

# Create a book
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'

# List all books
curl http://localhost:8080/books

# Filter by author
curl 'http://localhost:8080/books?author=Frank%20Herbert'

# Get one book
curl http://localhost:8080/books/1

# Update a book (only supplied fields change; title/author must stay valid)
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":1966}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1
```

## Tests

```sh
rebar3 eunit
```

The suite contains 12 tests across two modules:

- `test/book_store_tests.erl` — unit tests for the storage layer (create,
  validation, list/filter, update, delete, not-found handling).
- `test/booksapp_http_tests.erl` — integration tests that boot the full
  application and exercise every HTTP endpoint over a real socket.

## Project layout

```
src/
  booksapp_app.erl     Application callback; sets up routes and the listener
  booksapp_sup.erl     Top-level supervisor
  book_store.erl       gen_server wrapping the dets store (CRUD + validation)
  books_handler.erl    Cowboy handler for /books and /books/{id}
  health_handler.erl   Cowboy handler for /health
test/
  book_store_tests.erl
  booksapp_http_tests.erl
```
