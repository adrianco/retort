# Books API

A REST service for managing a book collection, written in Erlang with
[Cowboy](https://github.com/ninenines/cowboy) (HTTP) and SQLite via
[esqlite](https://github.com/mmzeeman/esqlite). JSON uses OTP's built-in `json` module.

## Requirements

- Erlang/OTP 27 or newer (developed on OTP 29)
- rebar3
- A C compiler (esqlite builds a NIF with a bundled copy of SQLite)

## Run

```sh
rebar3 shell
```

The server listens on port 8080 and stores data in `books.db` in the current
directory. Set `PORT` to change the port (`PORT=9000 rebar3 shell`); the
database path is the `db_path` application env in `src/books.app.src`.

## Test

```sh
rebar3 eunit
```

The tests start the application on port 18089 against an in-memory SQLite
database and exercise every endpoint over HTTP.

## API

A book is `{"id": 1, "title": "...", "author": "...", "year": 1965, "isbn": "..."}`.
`title` and `author` are required non-empty strings; `year` (integer) and `isbn`
(string) are optional and returned as `null` when absent.

| Method | Path          | Success | Errors |
|--------|---------------|---------|--------|
| GET    | `/health`     | 200 `{"status":"ok"}` | |
| POST   | `/books`      | 201 book, `Location` header | 400 malformed JSON, 422 validation |
| GET    | `/books`      | 200 array; `?author=` filters by exact author | |
| GET    | `/books/{id}` | 200 book | 400 bad id, 404 |
| PUT    | `/books/{id}` | 200 book (full replacement) | 400, 404, 422 |
| DELETE | `/books/{id}` | 204 no body | 400 bad id, 404 |

Errors are JSON: `{"error": "..."}`, with a per-field `details` object for
validation failures. Unsupported methods return 405.

```sh
curl -X POST localhost:8080/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'localhost:8080/books?author=Frank%20Herbert'
curl -X DELETE localhost:8080/books/1
```

## Layout

- `src/books_app.erl` — starts the supervisor and the Cowboy listener
- `src/books_db.erl` — gen_server owning the SQLite connection
- `src/books_handler.erl` — routing, validation and JSON responses
- `test/books_api_tests.erl` — EUnit tests

## macOS build note

esqlite 0.8.8 links its NIF without `-bundle`, which fails on current Apple
toolchains. `rebar.config.script` adds `-bundle` to `LDFLAGS` on macOS to work
around it; nothing needs to be done by hand.
