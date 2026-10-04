# Book API

A REST API for managing a book collection, written in Elixir with
[Plug](https://hexdocs.pm/plug) + [Bandit](https://hexdocs.pm/bandit) and
SQLite (via [exqlite](https://hexdocs.pm/exqlite)).

## Setup

Requires Elixir 1.15+ and a C compiler (exqlite builds the bundled SQLite if no
precompiled binary is available for your platform).

```sh
mix deps.get
mix compile
```

## Run

```sh
mix run --no-halt
```

The server listens on port 4000 and stores data in `books.db` in the current
directory. Override with environment variables:

```sh
PORT=8080 DATABASE_PATH=/tmp/books.db mix run --no-halt
```

## Test

```sh
mix test
```

Tests run against an in-memory SQLite database and do not open a port.

## API

A book is `{"id": 1, "title": "...", "author": "...", "year": 1965, "isbn": "..."}`.
`title` and `author` are required non-blank strings; `year` (integer) and `isbn`
(string) are optional.

| Method | Path          | Description                                   | Success | Errors        |
|--------|---------------|-----------------------------------------------|---------|---------------|
| GET    | `/health`     | Health check                                  | 200     |               |
| POST   | `/books`      | Create a book                                 | 201     | 400, 422      |
| GET    | `/books`      | List books; `?author=` filters (exact, case-insensitive) | 200 |        |
| GET    | `/books/{id}` | Get one book                                  | 200     | 404           |
| PUT    | `/books/{id}` | Replace a book (omitted optional fields become null) | 200 | 400, 404, 422 |
| DELETE | `/books/{id}` | Delete a book                                 | 204     | 404           |

Errors are JSON: `{"error": "..."}`; validation failures (422) also include
`"details": {"title": "is required"}`. Malformed JSON returns 400.

```sh
curl -X POST localhost:4000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'localhost:4000/books?author=Frank%20Herbert'
curl -X PUT localhost:4000/books/1 -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:4000/books/1
```
