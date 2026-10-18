# Books API

A small REST service for managing a book collection, built with Elixir,
[Plug](https://hexdocs.pm/plug), [Bandit](https://hexdocs.pm/bandit) and
SQLite (via [exqlite](https://hexdocs.pm/exqlite)).

## Requirements

- Elixir 1.15+ and Erlang/OTP 25+ (tested with Elixir 1.20 / OTP 29)
- A C compiler is only needed if exqlite has to build its NIF from source

## Setup

```sh
mix deps.get
```

## Run

```sh
mix run --no-halt
```

The server listens on port `4000` by default. Configure with environment variables:

| Variable        | Default     | Purpose                          |
|-----------------|-------------|----------------------------------|
| `PORT`          | `4000`      | HTTP port                        |
| `DATABASE_PATH` | `books.db`  | SQLite file (created on startup) |

## Test

```sh
mix test
```

Tests run against an in-memory SQLite database (`config/test.exs`).

## API

All request and response bodies are JSON.

| Method | Path          | Description                                  | Success |
|--------|---------------|----------------------------------------------|---------|
| POST   | `/books`      | Create a book                                | 201     |
| GET    | `/books`      | List books; optional `?author=` exact filter | 200     |
| GET    | `/books/{id}` | Get a single book                            | 200     |
| PUT    | `/books/{id}` | Replace a book's fields                      | 200     |
| DELETE | `/books/{id}` | Delete a book                                | 204     |
| GET    | `/health`     | Health check                                 | 200     |

Book fields: `title` (required, non-blank string), `author` (required,
non-blank string), `year` (optional integer, 0–9999), `isbn` (optional string).

PUT replaces all fields, so omitted optional fields are cleared.

### Examples

```sh
curl -X POST localhost:4000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl "localhost:4000/books?author=Frank%20Herbert"
curl localhost:4000/books/1
curl -X PUT localhost:4000/books/1 -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -X DELETE localhost:4000/books/1
```

### Errors

| Status | Cause                                                        |
|--------|--------------------------------------------------------------|
| 404    | Unknown book, non-integer id, or unknown route               |
| 422    | Validation failed; body is `{"error": ..., "details": {field: message}}` |
| 400    | Malformed JSON                                               |

## Project layout

- `lib/books_api/router.ex` — HTTP routes and status codes
- `lib/books_api/book.ex` — validation and persistence logic
- `lib/books_api/repo.ex` — GenServer owning the SQLite connection
- `test/books_api_test.exs` — router-level tests
