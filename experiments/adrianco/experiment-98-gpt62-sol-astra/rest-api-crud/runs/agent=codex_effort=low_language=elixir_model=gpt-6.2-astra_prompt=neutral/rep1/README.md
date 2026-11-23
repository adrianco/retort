# Book collection API

The service runs on Elixir 1.18+ (OTP 27+) using Plug and Bandit. Erlang's embedded DETS database stores the collection in `books.dets` and flushes each successful write to disk.

## Setup and run

```sh
mix local.hex --force
mix local.rebar --force
mix deps.get
mix compile
mix run --no-halt
```

The default port is 4000. Set `PORT` to change it or `BOOKS_DB` to select the database file in an existing writable directory. Run `mix test` to exercise the HTTP routes with an isolated temporary database.

## Endpoints

| Method | Path | Response |
|---|---|---|
| GET | /health | 200 with service status |
| POST | /books | 201 with the created book and a Location header |
| GET | /books | 200 with a JSON array ordered by ID. Use `?author=Name` for an exact match. |
| GET | /books/{id} | 200 with the book |
| PUT | /books/{id} | 200 with the replacement book |
| DELETE | /books/{id} | 204 with an empty body |

POST and PUT accept a JSON object with required nonblank strings `title` and `author`. Optional `year` (integer) and `isbn` (string) default to null. PUT preserves the ID and replaces all other fields. Missing books return 404, malformed JSON returns 400, and invalid fields return 422.

```sh
curl -i http://localhost:4000/books -H 'Content-Type: application/json' \
  -d '{"title":"Home","author":"Marilynne Robinson","year":2008}'
curl 'http://localhost:4000/books?author=Marilynne%20Robinson'
```
