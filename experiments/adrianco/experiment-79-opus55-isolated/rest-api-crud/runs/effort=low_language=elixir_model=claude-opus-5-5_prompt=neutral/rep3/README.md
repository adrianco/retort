# Book API

A small REST service for managing a book collection, written in Elixir with
[Plug](https://hexdocs.pm/plug) + [Bandit](https://hexdocs.pm/bandit) and
SQLite (via [exqlite](https://hexdocs.pm/exqlite)).

## Setup

Requires Elixir 1.15+ and a C compiler (exqlite builds the SQLite NIF if no
precompiled binary is available).

```sh
mix deps.get
```

## Run

```sh
mix run --no-halt
```

The server listens on port 4000 and stores data in `books.db`. Override with
environment variables:

```sh
PORT=8080 BOOKS_DB_PATH=/tmp/books.db mix run --no-halt
```

## Test

```sh
mix test
```

Tests use an in-memory SQLite database and do not open a port.

## API

A book is `{"id": 1, "title": "...", "author": "...", "year": 1965, "isbn": "..."}`.
`title` and `author` are required non-blank strings; `year` (integer) and
`isbn` (string) are optional.

| Method | Path          | Description                              | Success |
|--------|---------------|------------------------------------------|---------|
| GET    | `/health`     | Health check                             | 200     |
| POST   | `/books`      | Create a book                            | 201     |
| GET    | `/books`      | List books; `?author=` filters by exact author | 200 |
| GET    | `/books/{id}` | Fetch one book                           | 200     |
| PUT    | `/books/{id}` | Replace a book (full body; omitted optional fields become null) | 200 |
| DELETE | `/books/{id}` | Delete a book                            | 204     |

Errors are JSON:

- `400` — body is not valid JSON
- `404` — unknown book or route
- `422` — validation failed, e.g. `{"error": "validation failed", "details": {"title": "is required"}}`

Example:

```sh
curl -X POST localhost:4000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'localhost:4000/books?author=Frank%20Herbert'
```
