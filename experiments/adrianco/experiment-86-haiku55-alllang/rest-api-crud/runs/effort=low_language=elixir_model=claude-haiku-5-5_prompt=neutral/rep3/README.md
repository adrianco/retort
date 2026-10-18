# Book API

A REST API for managing a book collection, built with Elixir, Plug (Cowboy),
Ecto, and SQLite (via `ecto_sqlite3`).

## Requirements

- Elixir 1.15+ and Erlang/OTP 26+ (developed with Elixir 1.20 / OTP 29)

## Setup

```sh
mix deps.get
mix ecto.create
mix ecto.migrate
```

The SQLite database file is created in the project root (`book_api_dev.db`
in dev, `book_api_test.db` in test) and is git-ignored.

## Run

```sh
mix run --no-halt
```

The server listens on port `4000`.

## Test

```sh
mix test
```

The `test` alias creates and migrates the test database automatically.

## Endpoints

| Method | Path           | Description                          | Success |
|--------|----------------|--------------------------------------|---------|
| GET    | `/health`      | Health check                         | 200     |
| POST   | `/books`       | Create a book                        | 201     |
| GET    | `/books`       | List books; optional `?author=` filter | 200   |
| GET    | `/books/{id}`  | Get a book by ID                     | 200     |
| PUT    | `/books/{id}`  | Update a book (partial updates OK)   | 200     |
| DELETE | `/books/{id}`  | Delete a book                        | 204     |

A book has the fields `id`, `title`, `author`, `year`, `isbn`, `inserted_at`,
and `updated_at`. `title` and `author` are required and must be non-empty.
`year` (optional) must be between 1 and 9999. `isbn` (optional) is at most 20
characters.

Request bodies are JSON (`Content-Type: application/json`).

### Examples

```sh
curl -i localhost:4000/health

curl -i -X POST localhost:4000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl -s "localhost:4000/books?author=Frank%20Herbert"

curl -s -X PUT localhost:4000/books/1 \
  -H 'content-type: application/json' -d '{"year":1966}'

curl -i -X DELETE localhost:4000/books/1
```

### Errors

All errors are JSON:

- `404` — `{"error": "book not found"}` for unknown or malformed IDs, or
  `{"error": "not found"}` for unknown routes.
- `422` — `{"error": "validation failed", "details": {"title": ["is required"]}}`

## Project layout

```
lib/book_api/application.ex   OTP application; starts Repo and HTTP server
lib/book_api/repo.ex          Ecto repo (SQLite)
lib/book_api/book.ex          Schema and changeset (validation)
lib/book_api/books.ex         Context: persistence functions
lib/book_api/web/router.ex    Plug router / HTTP endpoints
priv/repo/migrations/         Database migrations
test/                         Unit and HTTP integration tests
```
