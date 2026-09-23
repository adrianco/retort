# Books REST API (Erlang/OTP)

A dependency-free book collection REST service. Requires Erlang/OTP 27+ (uses the built-in `json` module) and rebar3.

- HTTP: small HTTP/1.1 server on `gen_tcp` (`src/books_http.erl`)
- Storage: DETS, Erlang's built-in embedded disk store (used instead of SQLite, which would need a native NIF dependency) — `src/books_db.erl`
- Routing/validation: `src/books_api.erl`

## Run

```sh
rebar3 shell            # listens on port 8080, data in ./books.dets
```

Port and DB file are configured via the `port` and `db_file` app env (`src/books.app.src`).

## Endpoints

| Method | Path | Success | Errors |
|---|---|---|---|
| GET | /health | 200 `{"status":"ok"}` | |
| POST | /books | 201 book | 400 validation / bad JSON |
| GET | /books[?author=Name] | 200 list | |
| GET | /books/{id} | 200 book | 404 |
| PUT | /books/{id} | 200 book (full replace) | 400, 404 |
| DELETE | /books/{id} | 204 | 404 |

Body: `{"title": "...", "author": "...", "year": 1965, "isbn": "..."}` — `title` and `author` are required non-empty strings; `year` must be an integer and `isbn` a string if given.

```sh
curl -X POST localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl 'localhost:8080/books?author=Frank%20Herbert'
```

## Test

```sh
rebar3 eunit
```
