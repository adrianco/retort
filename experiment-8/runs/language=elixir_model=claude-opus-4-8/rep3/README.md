# Book API

A small REST API for managing a book collection, built in **Elixir** with
[Plug](https://hexdocs.pm/plug/) + [Cowboy](https://hexdocs.pm/plug_cowboy/) for
HTTP and [Ecto](https://hexdocs.pm/ecto/) + SQLite (via
[`ecto_sqlite3`](https://hexdocs.pm/ecto_sqlite3/)) for storage.

## Requirements

- Elixir `~> 1.15` and Erlang/OTP (tested on Elixir 1.19 / OTP 29)
- A C compiler (the `exqlite` SQLite driver is compiled on install)

## Setup

```bash
mix deps.get
mix ecto.create
mix ecto.migrate
```

## Run

```bash
mix run --no-halt
```

The server listens on **http://localhost:4000** (configurable via the `:port`
key in `config/config.exs`). The SQLite database is stored under `priv/`.

## Tests

```bash
mix test
```

The test suite (13 tests) covers the context module and every HTTP endpoint,
using an isolated SQLite test database with the Ecto SQL sandbox.

## API

All request and response bodies are JSON.

| Method   | Path           | Description                              | Success |
|----------|----------------|------------------------------------------|---------|
| `GET`    | `/health`      | Health check                             | `200`   |
| `POST`   | `/books`       | Create a book                            | `201`   |
| `GET`    | `/books`       | List books (optional `?author=` filter)  | `200`   |
| `GET`    | `/books/:id`   | Get a single book                        | `200`   |
| `PUT`    | `/books/:id`   | Update a book                            | `200`   |
| `DELETE` | `/books/:id`   | Delete a book                            | `204`   |

### Book fields

| Field    | Type    | Required | Notes                  |
|----------|---------|----------|------------------------|
| `title`  | string  | yes      |                        |
| `author` | string  | yes      |                        |
| `year`   | integer | no       |                        |
| `isbn`   | string  | no       |                        |

### Status codes

- `200 OK` — successful read/update
- `201 Created` — book created
- `204 No Content` — book deleted
- `404 Not Found` — book (or route) does not exist
- `422 Unprocessable Entity` — validation failed (e.g. missing `title`/`author`)

## Examples

```bash
# Health check
curl http://localhost:4000/health

# Create a book
curl -X POST http://localhost:4000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

# List all books
curl http://localhost:4000/books

# Filter by author
curl "http://localhost:4000/books?author=Frank%20Herbert"

# Get one book
curl http://localhost:4000/books/1

# Update a book
curl -X PUT http://localhost:4000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"Dune (Revised)"}'

# Delete a book
curl -X DELETE http://localhost:4000/books/1
```

## Project layout

```
lib/book_api/
  application.ex   # OTP application: starts the Repo and HTTP server
  repo.ex          # Ecto repo (SQLite adapter)
  book.ex          # Book schema + changeset/validation
  books.ex         # Context: CRUD operations
  router.ex        # Plug router: HTTP endpoints -> JSON
priv/repo/migrations/
  *_create_books.exs
test/
  book_api/books_test.exs    # context tests
  book_api/router_test.exs   # endpoint tests
```
