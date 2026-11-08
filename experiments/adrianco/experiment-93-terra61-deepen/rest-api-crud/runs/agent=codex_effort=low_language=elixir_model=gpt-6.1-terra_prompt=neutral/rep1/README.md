# Book collection API

An Elixir Plug/Bandit API backed by SQLite.

## Setup and run

Install Elixir 1.15 or newer, Erlang/OTP, and the build tools needed for SQLite's native dependency. Then run:

```sh
mix deps.get
mix run --no-halt
```

The service listens on port 4000 by default. Set `PORT` to change the port and `DATABASE_PATH` to change the SQLite file (default `books.db`). The table is created automatically at startup. Run tests with `mix test`.

## API

All request bodies are JSON objects. Books have an integer `id`, required nonblank `title` and `author`, and optional `year` (integer) and `isbn` (string). Updates accept any subset of fields and preserve omitted fields.

- `GET /health` returns `{"status":"ok"}`.
- `POST /books` creates a book and returns it with status 201.
- `GET /books` lists books in ID order. `?author=...` filters by exact author.
- `GET /books/:id` returns a book.
- `PUT /books/:id` updates and returns a book.
- `DELETE /books/:id` deletes a book and returns 204 with an empty body.

Missing books return 404, validation errors return 422 with an `errors` object, and malformed JSON returns 400.

```sh
curl -X POST http://localhost:4000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'http://localhost:4000/books?author=Frank%20Herbert'
```
