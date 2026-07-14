# Book API

A small REST API for managing a book collection, built with **Elixir**, **Plug + Cowboy**
for the HTTP layer, and **Ecto + SQLite3** for storage.

## Requirements

- Elixir `~> 1.15` and a compatible Erlang/OTP
- A C compiler (the SQLite driver, `exqlite`, compiles a NIF on install)

## Setup

```bash
mix deps.get
mix ecto.setup   # creates the SQLite database and runs migrations
```

## Run the server

```bash
mix run --no-halt
```

The API listens on `http://localhost:4000` (configurable via the `:port`
setting in `config/config.exs`). Migrations run automatically on startup in
dev/prod.

## Run the tests

```bash
mix test
```

The test suite (`test/book_api/router_test.exs`) covers the health check,
creation with validation errors, listing with the author filter, fetch,
update, and delete — 9 integration tests exercising the router end to end
against a sandboxed SQLite database.

## API

All responses are JSON.

### `GET /health`
Health check.
```json
{ "status": "ok" }
```

### `POST /books`
Create a book. `title` and `author` are required; `year` and `isbn` are optional.

```bash
curl -X POST http://localhost:4000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```

- `201 Created` with the created book on success
- `422 Unprocessable Entity` with `{"errors": {...}}` on validation failure

### `GET /books`
List all books, ordered by id. Supports a case-insensitive `?author=` substring filter.

```bash
curl http://localhost:4000/books
curl "http://localhost:4000/books?author=herbert"
```

- `200 OK` with a JSON array of books

### `GET /books/:id`
Fetch a single book.

- `200 OK` with the book
- `404 Not Found` if no book has that id

### `PUT /books/:id`
Update a book. Accepts any subset of `title`, `author`, `year`, `isbn`;
the same validation rules apply.

```bash
curl -X PUT http://localhost:4000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"Dune (Revised)"}'
```

- `200 OK` with the updated book
- `404 Not Found` if the book does not exist
- `422 Unprocessable Entity` on validation failure

### `DELETE /books/:id`
Delete a book.

- `204 No Content` on success
- `404 Not Found` if the book does not exist

## Project layout

```
config/                  app + per-environment configuration
lib/book_api/
  application.ex         OTP app: starts Repo + Cowboy, auto-migrates
  repo.ex                Ecto repo (SQLite3 adapter)
  book.ex                Book schema + changeset validations
  books.ex               Books context (data-access boundary)
  release.ex             migration helper
  web/router.ex          Plug router with all endpoints
priv/repo/migrations/    database schema
test/                    integration tests + DataCase helper
```
