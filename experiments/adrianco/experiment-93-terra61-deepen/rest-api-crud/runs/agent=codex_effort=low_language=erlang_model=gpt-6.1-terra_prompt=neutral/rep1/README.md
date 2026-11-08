# Book collection API

An Erlang/OTP service using Cowboy and the embedded Erlang DETS database. Data is stored in `books.dets` in the working directory and survives restarts. DETS is suitable for a single service instance; do not open the same database file from multiple instances.

## Setup and run

Install Erlang/OTP and rebar3. Dependencies are fetched by rebar3 on the first build.

```sh
rebar3 compile
rebar3 shell
```

The service starts automatically on port 8080. To change the port or database location, start it from an Erlang shell with the desired application settings before starting `books`:

```sh
erl -pa _build/default/lib/*/ebin
```

```erlang
application:load(books).
application:set_env(books, port, 9000).
application:set_env(books, db_file, "/path/to/books.dets").
application:ensure_all_started(books).
```

Run tests with `rebar3 eunit`.

## API

All responses, including errors, are JSON. `title` and `author` must be non-empty strings. `year` is optional (a positive integer or null) and `isbn` is optional (a string or null). Unknown fields are ignored. PUT replaces the complete book; omitted optional fields become null. IDs are positive integers assigned by the service.

- `GET /health` returns `200` and `{"status":"ok"}`.
- `POST /books` creates a book and returns it with status `201`.
- `GET /books` returns an array sorted by ID; `?author=...` filters by exact author.
- `GET /books/{id}` returns a book.
- `PUT /books/{id}` replaces a book and returns it.
- `DELETE /books/{id}` deletes a book and returns `{"deleted":true}`.

Missing books return `404`; invalid IDs, JSON, or fields return `400`; oversized bodies return `413`; unsupported methods return `405`.

```sh
curl -X POST http://localhost:8080/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'http://localhost:8080/books?author=Frank%20Herbert'
```
