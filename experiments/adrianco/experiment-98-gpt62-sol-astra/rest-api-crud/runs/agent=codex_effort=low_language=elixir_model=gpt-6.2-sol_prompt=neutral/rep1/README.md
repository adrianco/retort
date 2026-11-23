# Book Collection API

An Elixir REST API built with Plug, Bandit, and SQLite. The database and its schema are created on startup.

## Setup and run

Install Elixir 1.18 or later with a compatible Erlang/OTP release. Exqlite uses a precompiled native library where available. Building it from source requires a C compiler and make.

```sh
mix local.hex --force
mix deps.get
mix compile
mix run --no-halt
```

The server defaults to port 4000 and stores data in `book_collection.sqlite3` in the working directory. Set `PORT` and `BOOK_DB_PATH` to override those defaults. The database's parent directory must already exist.

## API

| Method and path | Success | Response |
| --- | --- | --- |
| `POST /books` | 201 | Created book and a `Location` header |
| `GET /books` | 200 | JSON array ordered by ID |
| `GET /books?author=Ursula%20K.%20Le%20Guin` | 200 | Books with the exact, case-sensitive author name |
| `GET /books/{id}` | 200 | Book |
| `PUT /books/{id}` | 200 | Replaced book |
| `DELETE /books/{id}` | 204 | Empty body |
| `GET /health` | 200 | `{"status":"ok"}` when SQLite responds |

For POST and PUT, send a JSON object with nonblank string values for `title` and `author`. Both fields are trimmed. Optional `year` accepts an integer and optional `isbn` accepts a string. Omitted or null optional fields are stored as null, including on PUT. A book response adds the database-generated integer `id`.

Invalid JSON or invalid IDs return 400. Invalid book fields return 422 with field-specific errors. A valid ID with no matching book returns 404.

```sh
curl -i http://localhost:4000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"A Wizard of Earthsea","author":"Ursula K. Le Guin","year":1968}'
```

## Tests

```sh
mix test
```

The tests exercise the Plug router and real SQLite queries using an in-memory database.
