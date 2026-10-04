# Book API

A REST service for managing a book collection, written in Elixir with
[Plug](https://hex.pm/packages/plug) + [Bandit](https://hex.pm/packages/bandit)
and SQLite (via [exqlite](https://hex.pm/packages/exqlite)).

## Setup

Requires Elixir 1.15+ and a C compiler (only if no precompiled SQLite NIF is
available for your platform).

```sh
mix deps.get
```

## Run

```sh
mix run --no-halt
```

The server listens on port 4000 and stores data in `books.db` in the current
directory. Both can be overridden with environment variables:

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
`title` and `author` are required non-blank strings; `year` (integer) and
`isbn` (string) are optional and default to `null`.

| Method | Path          | Success | Notes                                              |
|--------|---------------|---------|----------------------------------------------------|
| GET    | `/health`     | 200     | `{"status":"ok"}`                                  |
| POST   | `/books`      | 201     | Returns the created book                           |
| GET    | `/books`      | 200     | `?author=` filters by exact author, case-insensitive |
| GET    | `/books/{id}` | 200     |                                                    |
| PUT    | `/books/{id}` | 200     | Full replacement; omitted optional fields become `null` |
| DELETE | `/books/{id}` | 204     | Empty body                                         |

Errors are JSON too:

- `400` — malformed JSON, or a body that is not a JSON object
- `404` — unknown book or route: `{"error":"book not found"}`
- `422` — validation failure:
  `{"error":"validation failed","details":{"title":"is required"}}`

Example:

```sh
curl -X POST localhost:4000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'localhost:4000/books?author=Frank%20Herbert'
```
