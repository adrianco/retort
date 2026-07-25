# Book Collection API (C)

A small REST API for managing a book collection, written in C with a
hand-rolled HTTP/1.1 server, a minimal JSON parser/serializer, and
[SQLite](https://sqlite.org) for storage. No external HTTP or JSON
libraries are required — only the SQLite development headers.

## Layout

| File            | Purpose                                              |
|-----------------|------------------------------------------------------|
| `main.c`        | Socket HTTP server + request parsing                 |
| `api.c` / `.h`  | Routing and request handling (`api_handle`)          |
| `db.c` / `.h`   | SQLite persistence layer (CRUD)                      |
| `json.c` / `.h` | JSON parser and string-builder for responses         |
| `test.c`        | Integration + unit tests                             |
| `Makefile`      | Build / test targets                                 |

The routing logic (`api_handle`) is deliberately decoupled from the
socket layer so it can be tested directly against an in-memory database.

## Prerequisites

- A C compiler (`cc` / `gcc` / `clang`)
- `make`
- SQLite development headers (`libsqlite3-dev` on Debian/Ubuntu,
  `sqlite` via Homebrew on macOS — both ship the headers)

The Makefile uses `pkg-config` to locate SQLite, falling back to
`-lsqlite3` if `pkg-config` is unavailable.

## Build & run

```sh
make            # builds ./bookapi
./bookapi                 # listens on :8080, data in ./books.db
./bookapi 9000 mybooks.db # custom port and database file
```

Data persists in the SQLite file between runs.

## Run the tests

```sh
make test
```

This builds and runs `test_runner`, which exercises the full request
pipeline (create/read/update/delete, validation, filtering, routing)
against an in-memory SQLite database, plus unit tests for the JSON layer.

## API

All responses are JSON.

### `GET /health`
Liveness check.
```json
{ "status": "ok" }
```

### `POST /books`
Create a book. `title` and `author` are required; `year` and `isbn` are
optional.
```sh
curl -X POST http://localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'
```
`201 Created`
```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593" }
```
Missing/empty `title` or `author`, or a malformed body, returns
`400 Bad Request` with `{ "error": "..." }`.

### `GET /books`
List all books. Optional `?author=` filter (exact match, URL-encoded).
```sh
curl http://localhost:8080/books
curl "http://localhost:8080/books?author=Frank%20Herbert"
```
`200 OK` — a JSON array of book objects.

### `GET /books/{id}`
Fetch one book. `200 OK` with the object, or `404 Not Found`.

### `PUT /books/{id}`
Replace a book's fields (same validation as create). `200 OK` with the
updated object, `404 Not Found` if the id does not exist, or
`400 Bad Request` on invalid input.

### `DELETE /books/{id}`
Delete a book. `200 OK` with `{ "deleted": <id> }`, or `404 Not Found`.

## Status codes

| Code | Meaning                                             |
|------|-----------------------------------------------------|
| 200  | OK                                                  |
| 201  | Created                                             |
| 400  | Validation error / malformed JSON                   |
| 404  | Unknown route or missing book                       |
| 405  | Method not allowed on a known route                 |
| 500  | Internal/database error                             |

## Notes & limitations

- The server handles one connection at a time (sequential accept loop),
  which is sufficient for local use and testing. Add a thread/fork per
  connection for concurrency.
- `PUT` performs a full replace of the mutable fields rather than a
  partial patch.
