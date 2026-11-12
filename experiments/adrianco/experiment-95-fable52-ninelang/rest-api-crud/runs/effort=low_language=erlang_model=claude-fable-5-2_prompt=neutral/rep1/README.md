# Bookstore — a book collection REST API in Erlang

A small JSON REST service built with [Cowboy](https://github.com/ninenines/cowboy)
and SQLite (via the [esqlite](https://github.com/mmzeeman/esqlite) NIF).

## Requirements

- Erlang/OTP 27 or newer (uses the built-in `json` module; developed on OTP 29)
- `rebar3`
- A C compiler (esqlite compiles its bundled SQLite on first build)

## Run

```sh
rebar3 shell
```

The server listens on port 8080 and stores data in `books.db` in the current
directory. Both can be changed with environment variables:

```sh
PORT=9000 DB_PATH=/tmp/books.db rebar3 shell
```

(or the `port` / `db_path` keys of the `bookstore` application environment).

## Test

```sh
rebar3 eunit
```

The tests start the full application on a random port with an in-memory
database and exercise every endpoint over HTTP.

## API

A book looks like:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

`title` and `author` are required non-blank strings. `year` (integer) and
`isbn` (string) are optional and are `null` when absent.

| Method | Path          | Description                              | Success | Errors        |
|--------|---------------|------------------------------------------|---------|---------------|
| GET    | `/health`     | Health check, `{"status":"ok"}`          | 200     |               |
| POST   | `/books`      | Create a book                            | 201     | 400           |
| GET    | `/books`      | List books; `?author=` filters by exact author | 200 |             |
| GET    | `/books/{id}` | Fetch one book                           | 200     | 404           |
| PUT    | `/books/{id}` | Replace a book (same body as POST)       | 200     | 400, 404      |
| DELETE | `/books/{id}` | Delete a book                            | 204     | 404           |

Errors are JSON: `{"error": "..."}`; validation failures also carry a
`details` list, e.g. `{"error":"validation failed","details":["title is required"]}`.
Malformed JSON gives 400, unsupported methods 405.

### Example

```sh
curl -i -X POST localhost:8080/books -H 'content-type: application/json' \
     -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl 'localhost:8080/books?author=Frank%20Herbert'
curl -X PUT localhost:8080/books/1 -H 'content-type: application/json' \
     -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl -i -X DELETE localhost:8080/books/1
```

## Layout

- `src/bookstore_app.erl` — application start, routes, HTTP listener
- `src/bookstore_sup.erl` — supervisor
- `src/bookstore_db.erl` — SQLite storage (one process owns the connection)
- `src/bookstore_handler.erl` — HTTP handler and input validation
- `test/bookstore_tests.erl` — EUnit tests
- `rebar.config.script` — macOS-only workaround adding `-bundle` to `LDFLAGS`,
  without which esqlite's NIF fails to link
