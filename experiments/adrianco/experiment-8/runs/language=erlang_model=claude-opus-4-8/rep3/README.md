# Book API

A small REST API for managing a book collection, written in Erlang/OTP using
[Cowboy](https://github.com/ninenines/cowboy) for HTTP and **Mnesia** (Erlang's
built-in embedded database) for storage. JSON is handled with the standard
library `json` module (OTP 27+).

## Requirements

- Erlang/OTP 27 or newer (developed against OTP 29)
- [rebar3](https://rebar3.org/)

## Setup & Run

Fetch dependencies and compile:

```sh
rebar3 compile
```

Start the service (listens on port `8080` by default):

```sh
rebar3 shell
```

The server starts automatically as part of the `book_api` application. To use a
different port, set it before starting:

```sh
ERL_FLAGS="-book_api port 9000" rebar3 shell
```

## API

All request and response bodies are JSON.

| Method | Path           | Description                              |
| ------ | -------------- | ---------------------------------------- |
| GET    | `/health`      | Health check                             |
| POST   | `/books`       | Create a book                            |
| GET    | `/books`       | List books (optional `?author=` filter)  |
| GET    | `/books/{id}`  | Get a single book                        |
| PUT    | `/books/{id}`  | Update a book                            |
| DELETE | `/books/{id}`  | Delete a book                            |

A book has the fields: `id` (assigned by the server), `title`, `author`,
`year`, and `isbn`. **`title` and `author` are required** on creation.

### Examples

```sh
# Health check
curl http://localhost:8080/health
# {"status":"ok"}

# Create a book
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
# 201 Created
# {"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}

# List all books
curl http://localhost:8080/books

# Filter by author
curl 'http://localhost:8080/books?author=Frank%20Herbert'

# Get one book
curl http://localhost:8080/books/1

# Update a book (only the provided fields change)
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":1966}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1
# 204 No Content
```

### Status codes

- `200 OK` — successful GET/PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — invalid JSON, or missing/empty `title`/`author`
- `404 Not Found` — no book with the given id
- `405 Method Not Allowed` — unsupported method on a route

## Tests

The suite spins up the real HTTP server and exercises every endpoint
end-to-end (10 test cases):

```sh
rebar3 ct
```

## Project layout

```
src/
  book_api.app.src   application metadata
  book_api_app.erl   application start/stop, routing, listener
  book_api_sup.erl   top-level supervisor
  book_handler.erl   /books and /books/{id} request handling + validation
  health_handler.erl /health endpoint
  book_store.erl     Mnesia-backed storage layer
  book_records.hrl   record definitions
test/
  book_api_SUITE.erl Common Test integration tests
```

## Notes

Mnesia is configured with `ram_copies`, so the collection lives in memory for
the lifetime of the node. Swapping the tables to `disc_copies` in
`book_store:init/0` is all that's needed to persist data across restarts.
