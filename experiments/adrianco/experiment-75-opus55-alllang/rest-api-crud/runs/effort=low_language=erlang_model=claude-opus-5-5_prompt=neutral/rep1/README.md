# Books REST API (Erlang)

A zero-dependency REST service built on OTP: `inets` httpd for HTTP, the OTP 27+ `json`
module, and DETS (Erlang's built-in embedded disk store, used in place of SQLite so no
native drivers are needed).

## Requirements
Erlang/OTP 27+ and rebar3.

## Run
```sh
rebar3 shell        # serves on http://localhost:8080, data in ./books.dets
```
Port and DB file are configurable via the `port` and `db_file` app env (`src/books.app.src`).

## Endpoints
| Method | Path | Notes |
|---|---|---|
| GET | /health | `{"status":"ok"}` |
| POST | /books | body `{title, author, year?, isbn?}` → 201 |
| GET | /books[?author=X] | list, optional exact-author filter |
| GET | /books/{id} | 200 / 404 |
| PUT | /books/{id} | full replace, same validation → 200 / 400 / 404 |
| DELETE | /books/{id} | 204 / 404 |

`title` and `author` are required non-empty strings; `year` must be an integer and `isbn` a string. Validation errors return 400 with `details`.

## Test
```sh
rebar3 ct
```
