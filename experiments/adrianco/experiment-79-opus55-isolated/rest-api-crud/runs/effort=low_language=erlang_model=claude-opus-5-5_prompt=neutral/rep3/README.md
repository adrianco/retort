# Book API

A REST service for managing a book collection, written in Erlang/OTP.

- HTTP server: [Cowboy](https://github.com/ninenines/cowboy) 2.12
- Storage: DETS, OTP's built-in embedded on-disk database (the Erlang
  equivalent of SQLite — no native dependencies to compile)
- JSON: the `json` module from the standard library

## Requirements

- Erlang/OTP 27 or newer (for the built-in `json` module)
- rebar3

## Run

```sh
rebar3 shell
```

The server listens on port 8080 and stores data in `books.dets` in the
current directory. Both can be overridden with environment variables:

```sh
PORT=9000 BOOKS_DB=/var/tmp/books.dets rebar3 shell
```

## Test

```sh
rebar3 eunit
```

The tests start the real application on an ephemeral port with a temporary
database file and exercise every endpoint over HTTP.

## API

A book looks like this:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

| Method | Path          | Description                                  | Success |
|--------|---------------|----------------------------------------------|---------|
| GET    | `/health`     | Health check, returns `{"status":"ok"}`      | 200     |
| POST   | `/books`      | Create a book                                | 201     |
| GET    | `/books`      | List books; `?author=` filters by exact author | 200   |
| GET    | `/books/{id}` | Fetch one book                               | 200     |
| PUT    | `/books/{id}` | Replace a book (full body, same rules as POST) | 200   |
| DELETE | `/books/{id}` | Delete a book                                | 204     |

Validation:

- `title` and `author` are required, non-blank strings (surrounding
  whitespace is trimmed).
- `year` is optional and must be an integer; `isbn` is optional and must be a
  string. Omitted optional fields are stored as `null`.

Error responses are JSON objects with an `error` message:

| Status | When                                                       |
|--------|------------------------------------------------------------|
| 400    | Malformed JSON, non-object body, or a non-numeric id       |
| 404    | No book with that id                                       |
| 405    | Method not supported on the path                           |
| 413    | Body larger than 1 MB                                      |
| 422    | Validation failed; `details` maps each bad field to a reason |

### Example

```sh
curl -i -X POST localhost:8080/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'localhost:8080/books?author=Frank%20Herbert'
curl -X PUT localhost:8080/books/1 -H 'content-type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -i -X DELETE localhost:8080/books/1
```

## Layout

- `src/book_api_app.erl` — application start, routes, HTTP listener
- `src/book_api_sup.erl` — supervisor
- `src/book_store.erl` — DETS-backed storage gen_server
- `src/book_api_books_handler.erl` — `/books` handlers and validation
- `src/book_api_health_handler.erl` — `/health`
- `test/book_api_tests.erl` — EUnit unit and integration tests
