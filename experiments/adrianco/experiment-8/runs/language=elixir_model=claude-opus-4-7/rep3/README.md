# BookApi

A small REST API for managing a book collection, built with Elixir / Plug /
Bandit, with data stored in SQLite via Ecto.

## Requirements

- Elixir 1.15+ (tested with Elixir 1.19 / Erlang 29)
- A C toolchain (for compiling the `exqlite` NIF)

## Setup

```sh
mix deps.get
mix ecto.setup     # creates the SQLite DB and runs the migration
```

## Run

```sh
mix run --no-halt
```

The server listens on port `4000` by default. Override with the `PORT`
environment variable:

```sh
PORT=8080 mix run --no-halt
```

## Test

```sh
mix test
```

The test suite uses a separate SQLite database (`book_api_test.db`) and the
Ecto SQL sandbox so tests run in transactions and leave no residue.

## Endpoints

| Method | Path           | Description                              |
|--------|----------------|------------------------------------------|
| GET    | `/health`      | Health check, returns `{"status":"ok"}`  |
| GET    | `/books`       | List books (filter with `?author=Name`)  |
| GET    | `/books/:id`   | Fetch one book                           |
| POST   | `/books`       | Create a book                            |
| PUT    | `/books/:id`   | Update a book                            |
| DELETE | `/books/:id`   | Delete a book (204 No Content)           |

### Request / response shape

A book has the fields `title` (required, string), `author` (required, string),
`year` (optional integer), `isbn` (optional string).

```sh
curl -X POST http://localhost:4000/books \
  -H "content-type: application/json" \
  -d '{"title":"Programming Elixir","author":"Dave Thomas","year":2018,"isbn":"978-1680502992"}'
```

```json
{
  "id": 1,
  "title": "Programming Elixir",
  "author": "Dave Thomas",
  "year": 2018,
  "isbn": "978-1680502992",
  "inserted_at": "2026-06-04T10:50:00Z",
  "updated_at": "2026-06-04T10:50:00Z"
}
```

### Status codes

- `200 OK` — successful GET/PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `404 Not Found` — unknown route or missing book id
- `422 Unprocessable Entity` — validation failed; body includes
  `{"errors": {"field": ["message", ...]}}`

## Project layout

```
lib/book_api/
  application.ex   # OTP application, starts Repo + Bandit
  repo.ex          # Ecto repo (SQLite3 adapter)
  book.ex          # Ecto schema + changeset
  books.ex         # context — list/get/create/update/delete
  router.ex        # Plug.Router with all endpoints
priv/repo/migrations/
  20260604000000_create_books.exs
test/book_api/
  router_test.exs  # integration tests for all endpoints
```
