# Books API

A REST API service for managing a book collection, written in Elixir using
[Plug](https://hexdocs.pm/plug) + [Bandit](https://hexdocs.pm/bandit) for HTTP
and [Ecto](https://hexdocs.pm/ecto) with SQLite (`ecto_sqlite3`) for storage.

## Requirements

- Elixir ~> 1.15 (tested with 1.20 / OTP 29)

## Setup

```sh
mix deps.get
mix ecto.create
mix ecto.migrate
```

## Run

```sh
mix run --no-halt
```

The server listens on port 4000 by default. Override with the `PORT`
environment variable in prod, or change `config/config.exs`. The SQLite
database file lives at `priv/repo/books_api_<env>.db`.

## Test

```sh
mix test
```

The `test` alias creates and migrates a dedicated test database
automatically before running the suite (13 tests covering the context layer
and full request/response cycles through the router).

## API

| Method | Path            | Description                              |
|--------|-----------------|------------------------------------------|
| GET    | `/health`       | Health check → `{"status": "ok"}`        |
| POST   | `/books`        | Create a book (201, or 422 on invalid)   |
| GET    | `/books`        | List books; supports `?author=` filter   |
| GET    | `/books/{id}`   | Get one book (404 if missing)            |
| PUT    | `/books/{id}`   | Update a book (200 / 404 / 422)          |
| DELETE | `/books/{id}`   | Delete a book (204 / 404)                |

A book has `title` (required), `author` (required), `year` (optional
positive integer), and `isbn` (optional string). Validation failures return
`422` with a JSON `errors` map; unknown routes return `404`.

### Examples

```sh
curl -X POST localhost:4000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Release It!","author":"Michael Nygard","year":2007,"isbn":"978-1680502398"}'

curl 'localhost:4000/books?author=Michael%20Nygard'

curl localhost:4000/books/1

curl -X PUT localhost:4000/books/1 \
  -H 'content-type: application/json' \
  -d '{"year":2018}'

curl -X DELETE localhost:4000/books/1
```

## Project layout

- `lib/books_api/router.ex` — HTTP routing, JSON encoding, error handling
- `lib/books_api/books.ex` — CRUD context around the repo
- `lib/books_api/book.ex` — Ecto schema and changeset validation
- `lib/books_api/repo.ex` — SQLite-backed Ecto repo
- `priv/repo/migrations/` — database migrations
- `test/` — context and router integration tests
