# Books API

A REST API for managing a book collection, written in Erlang/OTP. It uses
[Cowboy](https://github.com/ninenines/cowboy) for HTTP, [esqlite](https://github.com/mmzeeman/esqlite)
for SQLite storage, and the built-in `json` module for JSON.

## Requirements

- Erlang/OTP 27 or newer (the built-in `json` module; developed on OTP 29)
- [rebar3](https://rebar3.org/)
- A C compiler (esqlite builds its SQLite NIF from source)

## Setup

```sh
rebar3 compile
```

The first build downloads dependencies from hex.pm.

On macOS, the project's `rebar.config` contains an override that adds the `-bundle`
link flag to esqlite. Without it the SQLite NIF links as an executable and cannot be
loaded. No action is needed; the override applies automatically.

## Run

```sh
rebar3 shell
```

The server listens on port `8080` and stores data in `books.db` in the current
directory. Both can be changed with environment variables:

| Variable        | Default     | Purpose                    |
|-----------------|-------------|----------------------------|
| `BOOKS_PORT`    | `8080`      | HTTP port                  |
| `BOOKS_DB_PATH` | `books.db`  | Path to the SQLite database |

```sh
BOOKS_PORT=9000 BOOKS_DB_PATH=/tmp/books.db rebar3 shell
```

## Test

```sh
rebar3 eunit
```

The suite has two parts:

- `test/books_validate_tests.erl` covers input validation rules.
- `test/books_api_tests.erl` starts the whole application on a temporary database and
  port, then exercises every endpoint over real HTTP.

## API

A book has the following fields:

| Field    | Type                 | Required | Notes                              |
|----------|----------------------|----------|------------------------------------|
| `id`     | integer              | (server) | Assigned on creation               |
| `title`  | string               | yes      | Non-empty after trimming           |
| `author` | string               | yes      | Non-empty after trimming           |
| `year`   | non-negative integer | no       | `null` when omitted                |
| `isbn`   | string               | no       | `null` when omitted                |

### Endpoints

| Method   | Path          | Description                                     | Success |
|----------|---------------|-------------------------------------------------|---------|
| `POST`   | `/books`      | Create a book                                   | `201`   |
| `GET`    | `/books`      | List books; `?author=` filters by author        | `200`   |
| `GET`    | `/books/{id}` | Get one book                                    | `200`   |
| `PUT`    | `/books/{id}` | Replace a book (full representation required)   | `200`   |
| `DELETE` | `/books/{id}` | Delete a book                                   | `204`   |
| `GET`    | `/health`     | Health check; verifies the database is reachable | `200`   |

`PUT` replaces the whole book, so `title` and `author` are required on update too.
Omitted `year` or `isbn` are stored as `null`.

The `author` filter matches the full author name, ignoring case.

### Examples

```sh
# Create
curl -i -X POST http://localhost:8080/books \
  -H 'content-type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}'

# List, or filter by author
curl http://localhost:8080/books
curl 'http://localhost:8080/books?author=frank%20herbert'

# Get, update, delete
curl http://localhost:8080/books/1
curl -X PUT http://localhost:8080/books/1 \
  -H 'content-type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965}'
curl -i -X DELETE http://localhost:8080/books/1

# Health
curl http://localhost:8080/health
```

### Errors

Error responses have the form `{"error": "..."}`. Validation failures also include
`"details"` with one message per invalid field.

| Status | When                                                              |
|--------|-------------------------------------------------------------------|
| `400`  | Body is not valid JSON, not a JSON object, or fails validation    |
| `404`  | Book does not exist, or the id is not a positive integer          |
| `405`  | HTTP method not supported on the path (response includes `Allow`) |
| `404`  | Path does not match any route                                     |
| `503`  | `/health` cannot reach the database                               |

Example validation error:

```json
{
  "error": "validation failed",
  "details": ["title is required", "year must be a non-negative integer"]
}
```

## Project layout

```
src/
  books_app.erl                  application callback; starts cowboy and the supervisor
  books_sup.erl                  supervisor for the database process
  books_db.erl                   gen_server owning the SQLite connection
  books_validate.erl             pure input validation
  books_http.erl                 shared JSON helpers
  books_health_handler.erl       GET /health
  books_collection_handler.erl   /books
  books_item_handler.erl         /books/{id}
test/
  books_validate_tests.erl       validation unit tests
  books_api_tests.erl            HTTP integration tests
```
