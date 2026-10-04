# Books API

A REST service for managing a book collection, written in Erlang with
[Cowboy](https://github.com/ninenines/cowboy) for HTTP and SQLite (via
[esqlite](https://github.com/mmzeeman/esqlite)) for storage.

## Requirements

- Erlang/OTP 27 or later (uses the built-in `json` module)
- rebar3
- A C compiler (esqlite builds its bundled SQLite as a NIF)

## Build and run

```sh
rebar3 compile
rebar3 shell
```

The server listens on port 8080 and stores data in `books.db` in the current
directory. Both are application environment settings and can be overridden:

```sh
erl -pa _build/default/lib/*/ebin -books port 9090 -books db_path '"/tmp/books.db"' \
    -eval 'application:ensure_all_started(books).'
```

## Tests

```sh
rebar3 do eunit, ct
```

- `test/books_validate_tests.erl` — EUnit tests for input validation.
- `test/books_SUITE.erl` — Common Test integration suite that starts the
  application on port 18089 against a temporary database and calls every
  endpoint over HTTP.

## API

A book is `{"id": 1, "title": "...", "author": "...", "year": 1965, "isbn": "..."}`.
`title` and `author` are required non-empty strings; `year` (integer) and
`isbn` (string) are optional and returned as `null` when absent.

| Method | Path          | Success          | Errors                          |
|--------|---------------|------------------|---------------------------------|
| GET    | `/health`     | 200 `{"status":"ok"}` |                            |
| POST   | `/books`      | 201, created book, `Location` header | 400 invalid JSON or validation failure |
| GET    | `/books`      | 200, array of books; `?author=` filters by exact author | |
| GET    | `/books/{id}` | 200, book        | 404                             |
| PUT    | `/books/{id}` | 200, updated book | 400, 404                       |
| DELETE | `/books/{id}` | 204, no body     | 404                             |

`PUT` replaces the whole book, so omitted optional fields are reset to `null`.
Errors are JSON: `{"error": "validation failed", "details": ["title is required"]}`.
Unsupported methods return 405.

```sh
curl -X POST localhost:8080/books -H 'content-type: application/json' \
     -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'localhost:8080/books?author=Frank%20Herbert'
curl -X DELETE localhost:8080/books/1
```

## Layout

- `src/books_app.erl`, `src/books_sup.erl` — application, routes, supervision
- `src/books_db.erl` — gen_server owning the SQLite connection
- `src/books_handler.erl` — `/books` handlers and validation
- `src/books_health_handler.erl` — `/health`
