# Books REST API (Erlang/OTP)

A dependency-free book collection REST API: a small HTTP/1.1 server on `gen_tcp`,
JSON through OTP's built-in `json` module, and storage in DETS (Erlang's embedded
disk database, used here in place of SQLite).

## Requirements
- Erlang/OTP 27+ (for the `json` module)
- rebar3

## Run
```sh
rebar3 shell            # listens on :8080, stores data in books.dets
```
To change the port or DB file, edit `src/books.app.src` `env` or run
`application:set_env(books, port, 9000)` before the app starts.

## Endpoints
| Method | Path | Notes |
|---|---|---|
| GET | /health | `{"status":"ok"}` |
| POST | /books | body `{"title","author","year"?,"isbn"?}` → 201 |
| GET | /books[?author=Name] | list, optional exact author filter |
| GET | /books/{id} | 200 / 404 |
| PUT | /books/{id} | full replacement, same validation → 200 / 400 / 404 |
| DELETE | /books/{id} | 204 / 404 |

`title` and `author` are required, non-blank strings. `year` must be an integer and `isbn` a string. If validation fails, the API returns 400 with a `details` list.

```sh
curl -XPOST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
```

## Test
```sh
rebar3 eunit
```
The tests cover validation unit tests and HTTP integration tests (health, CRUD, author filter, bad input).
