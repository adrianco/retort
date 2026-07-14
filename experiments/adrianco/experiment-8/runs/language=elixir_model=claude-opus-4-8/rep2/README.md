# Book API

A small REST API for managing a book collection, written in Elixir using
[Plug](https://hexdocs.pm/plug) + [Bandit](https://hexdocs.pm/bandit) for HTTP
and [Ecto](https://hexdocs.pm/ecto) with **SQLite** (`ecto_sqlite3`) for storage.

## Requirements

- Elixir `~> 1.15` and Erlang/OTP (developed against Elixir 1.19 / OTP 29)

## Setup

```bash
mix deps.get
mix ecto.create   # creates the SQLite database file under priv/
mix ecto.migrate  # creates the books table
```

## Run

```bash
mix run --no-halt
```

The server listens on **http://localhost:4000** (override with the `PORT`
environment variable in `MIX_ENV=prod`).

## Run the tests

```bash
MIX_ENV=test mix ecto.create
MIX_ENV=test mix ecto.migrate
mix test
```

## API

All request and response bodies are JSON.

| Method   | Path           | Description                                  |
|----------|----------------|----------------------------------------------|
| `GET`    | `/health`      | Health check — returns `{"status":"ok"}`     |
| `POST`   | `/books`       | Create a book                                |
| `GET`    | `/books`       | List books (optional `?author=` filter)      |
| `GET`    | `/books/:id`   | Fetch a single book                          |
| `PUT`    | `/books/:id`   | Update a book                                |
| `DELETE` | `/books/:id`   | Delete a book                                |

### Book fields

- `title` *(string, required)*
- `author` *(string, required)*
- `year` *(integer, optional)*
- `isbn` *(string, optional)*

### Status codes

- `200 OK` — successful read/update
- `201 Created` — book created
- `204 No Content` — book deleted
- `404 Not Found` — book does not exist / unknown route
- `422 Unprocessable Entity` — validation failed (e.g. missing `title`/`author`)

### Examples

```bash
# Create
curl -X POST localhost:4000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

# List all / filter by author
curl localhost:4000/books
curl 'localhost:4000/books?author=Frank%20Herbert'

# Fetch one
curl localhost:4000/books/1

# Update
curl -X PUT localhost:4000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"Dune (Deluxe Edition)"}'

# Delete
curl -X DELETE localhost:4000/books/1
```

A validation failure returns the offending fields:

```json
{"errors": {"title": ["can't be blank"], "author": ["can't be blank"]}}
```

## Project layout

```
lib/book_api/
  application.ex  # OTP app: starts Repo + Bandit HTTP server
  repo.ex         # Ecto repo (SQLite3 adapter)
  book.ex         # Book schema + changeset (validation)
  books.ex        # Context: CRUD + author filtering
  router.ex       # Plug router mapping HTTP routes to the context
  release.ex      # Migration helper for releases
priv/repo/migrations/  # Database migrations
test/                  # Context + router (integration) tests
```
