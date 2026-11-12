# Book API

A REST API for managing a book collection, written in Elixir with
[Plug](https://hex.pm/packages/plug) + [Bandit](https://hex.pm/packages/bandit)
and SQLite (via [exqlite](https://hex.pm/packages/exqlite)).

## Requirements

- Elixir 1.18+ (uses the built-in `JSON` module) and Erlang/OTP 27+

## Setup and run

```sh
mix deps.get
mix run --no-halt
```

The server listens on port 4000 and stores data in `books.db`. Both are
configurable through environment variables:

```sh
PORT=8080 DATABASE_PATH=/tmp/books.db mix run --no-halt
```

## Tests

```sh
mix test
```

Tests run against an in-memory SQLite database and do not start the HTTP listener.

## API

A book is `{"id": 1, "title": "...", "author": "...", "year": 1965, "isbn": "..."}`.
`title` and `author` are required non-blank strings; `year` (integer) and
`isbn` (string) are optional.

| Method | Path          | Description                              | Success | Errors        |
|--------|---------------|------------------------------------------|---------|---------------|
| GET    | `/health`     | Health check                             | 200     |               |
| POST   | `/books`      | Create a book                            | 201     | 400, 422      |
| GET    | `/books`      | List books; `?author=` filters by exact author | 200 |             |
| GET    | `/books/{id}` | Get one book                             | 200     | 404           |
| PUT    | `/books/{id}` | Replace a book (full payload required)   | 200     | 400, 404, 422 |
| DELETE | `/books/{id}` | Delete a book                            | 204     | 404           |

Errors are JSON: `{"error": "..."}`. Validation failures return 422 with
per-field details, e.g. `{"error": "validation failed", "details": {"title": "is required"}}`.
Malformed JSON returns 400.

### Example

```sh
curl -X POST localhost:4000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'localhost:4000/books?author=Frank%20Herbert'
curl -X DELETE localhost:4000/books/1
```

## Layout

- `lib/book_api/router.ex` — HTTP routes
- `lib/book_api/book.ex` — payload validation
- `lib/book_api/store.ex` — SQLite storage (a GenServer owning the connection)
- `test/book_api_test.exs` — integration tests through the router
