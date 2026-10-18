# Books API (C + SQLite)

A small REST service for managing a book collection. Written in C (C11), with
data stored in SQLite and a minimal HTTP/1.1 server built on POSIX sockets.

## Requirements

- A C compiler (`cc`/`clang`/`gcc`) and `make`
- SQLite 3 development files
  - macOS: ships with the system SDK, nothing to install
  - Debian/Ubuntu: `sudo apt install build-essential libsqlite3-dev`
  - Fedora: `sudo dnf install gcc make sqlite-devel`

## Build, run, test

```sh
make            # builds bin/books-api
make test       # builds and runs bin/test_api
./bin/books-api [port] [db-path]
```

Defaults: port `8080`, database file `books.db` in the current directory. The
database schema is created on first start. The server listens on `127.0.0.1`
only.

## Data model

| field    | type    | required | notes                                        |
|----------|---------|----------|----------------------------------------------|
| `id`     | integer | server   | assigned on create, read-only                |
| `title`  | string  | yes      | non-blank, at most 255 bytes                 |
| `author` | string  | yes      | non-blank, at most 255 bytes                 |
| `year`   | integer | no       | 0–9999, `null` when absent                   |
| `isbn`   | string  | no       | ISBN-10 or ISBN-13, hyphens allowed, `null` when absent |

Note that `isbn` is checked for format only, not for its check digit.

## Endpoints

| Method   | Path          | Success                    | Errors                          |
|----------|---------------|----------------------------|---------------------------------|
| `POST`   | `/books`      | `201` with the created book | `400` invalid body              |
| `GET`    | `/books`      | `200` JSON array           | `400` empty or malformed `author` |
| `GET`    | `/books/{id}` | `200` with the book        | `404` not found                 |
| `PUT`    | `/books/{id}` | `200` with the updated book | `400` invalid body, `404` not found |
| `DELETE` | `/books/{id}` | `204` no content           | `404` not found                 |
| `GET`    | `/health`     | `200` `{"status":"ok"}`    |                                 |

`GET /books?author=...` returns only books whose author matches exactly. The
value is percent-decoded, so `author=Frank%20Herbert` and `author=Frank+Herbert`
both work. An empty `author=` is rejected with `400`.

`PUT` replaces the whole record, so `title` and `author` are required again.
Omitted `year` or `isbn` are cleared.

Errors come back as JSON: `{"error": "..."}`. Unknown paths return `404`, and
known paths with an unsupported method return `405`.

## Examples

```sh
curl -i -X POST http://127.0.0.1:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'

curl 'http://127.0.0.1:8080/books?author=Frank%20Herbert'
curl http://127.0.0.1:8080/books/1
curl -X PUT http://127.0.0.1:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -X DELETE http://127.0.0.1:8080/books/1
curl http://127.0.0.1:8080/health
```

## Layout

```
src/
  buf.[ch]     growable string buffer
  json.[ch]    small JSON parser (objects, strings, numbers) and string escaping
  book.[ch]    book validation, SQLite storage
  api.[ch]     request routing and handlers (no sockets; testable in-process)
  http.[ch]    HTTP/1.1 request parsing and response writing
  main.c       entry point
tests/
  test_api.c   unit, handler, and socket-level integration tests
```

## Limits and design notes

- Requests are handled one at a time. Each connection gets `Connection: close`,
  and a 5-second read timeout keeps a stalled client from blocking the server.
- Request headers are limited to 8 KiB and bodies to 1 MiB. Chunked request
  bodies are not supported (`501`); send `Content-Length`.
- Only IPv4 loopback is bound. Put a reverse proxy in front of it if you need
  remote access, and add authentication there, since the API has none.
