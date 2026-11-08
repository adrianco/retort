# Book collection API

A JSON REST API built with Elixir, Plug, Bandit and SQLite.

## Setup and run

Install Elixir 1.15 or later, Erlang, a C compiler and make (needed to build the SQLite dependency). Then run:

```sh
mix deps.get
mix run --no-halt
```

The server listens on port 4000 by default. Set `PORT` to change it and `DATABASE_PATH` to change the SQLite file (default `books_dev.db`). The database and table are created automatically on startup. Run tests with `mix test`; tests use `books_test.db` by default.

## API

Send JSON with `Content-Type: application/json`. Books have `id`, `title`, `author`, `year` and `isbn`. Title and author are required nonblank strings; year is an integer and ISBN is a string, both optional.

- `GET /health` returns `{"status":"ok"}`.
- `POST /books` creates a book and returns it with status 201.
- `GET /books` returns an array; `?author=...` filters by exact author.
- `GET /books/:id` returns a book.
- `PUT /books/:id` updates supplied fields and returns the book. Omitted fields are retained.
- `DELETE /books/:id` deletes a book and returns 204 with an empty body.

Missing books return 404. Invalid fields return 422 with an `errors` object. For example:

```sh
curl -X POST localhost:4000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
```
