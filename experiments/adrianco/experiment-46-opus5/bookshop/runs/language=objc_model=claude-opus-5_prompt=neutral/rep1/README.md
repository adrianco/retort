# bookapi — a Book Collection REST API in Objective-C

A small REST service for managing a book collection, written in plain
Objective-C (ARC) against Foundation, with SQLite for storage and a
purpose-built HTTP/1.1 server on top of BSD sockets and GCD.

**No third-party dependencies** — it builds with the stock macOS toolchain
(`clang`, `Foundation.framework`, `libsqlite3`), which ships with the Xcode
Command Line Tools.

## Requirements

- macOS with the Xcode Command Line Tools (`xcode-select --install`)
- `make`

## Build and run

```sh
make build                 # -> build/bookapi
make run                   # listens on :8080, database ./books.db
make run PORT=9000 DB=/tmp/books.db
```

Or invoke the binary directly:

```sh
./build/bookapi --port 8080 --db books.db --host 127.0.0.1
```

| Flag / variable | Default   | Meaning                                          |
| --------------- | --------- | ------------------------------------------------ |
| `--port N`      | `8080`    | TCP port; `0` asks the kernel for a free port     |
| `--db PATH`     | `books.db`| SQLite file; `:memory:` for an ephemeral database |
| `--host ADDR`   | `0.0.0.0` | Bind address                                      |
| `PORT` (env)    | —         | Port fallback when `--port` is not given          |
| `BOOKS_DB` (env)| —         | Database fallback when `--db` is not given        |

The database file and its schema are created on first start.
`SIGINT`/`SIGTERM` shut the service down cleanly.

## Tests

```sh
make test
```

23 tests / 149 assertions covering the storage layer, the router, and the
service end-to-end over a real socket. XCTest is not available with the
standalone Command Line Tools, so `tests/TestSupport.h` provides a small
block-based harness; the runner exits non-zero if anything fails.

The suite is also clean under sanitizers:

```sh
make clean && make test CFLAGS="-std=gnu11 -fobjc-arc -g -O1 -fsanitize=address,undefined"
make clean && make test CFLAGS="-std=gnu11 -fobjc-arc -g -O1 -fsanitize=thread"
```

## API

All responses are JSON (`application/json; charset=utf-8`), except `204 No
Content` on delete.

### `GET /health`

```json
{"database": "up", "service": "bookapi", "status": "ok"}
```

`200` when the database answers, `503` otherwise.

### `POST /books`

```sh
curl -X POST localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```

`201 Created` with the stored book and a `Location: /books/{id}` header.

### `GET /books` · `GET /books?author=NAME`

Returns a JSON array ordered by id. The `author` filter is an exact,
case-insensitive match and is percent-decoded (`?author=Frank%20Herbert` and
`?author=Frank+Herbert` both work). An empty value means "no filter".

### `GET /books/{id}`

`200` with the book, or `404` if it does not exist.

### `PUT /books/{id}`

Full replacement: `title` and `author` are required, and any omitted optional
field is cleared. `200` with the updated book, `404` if it does not exist.

### `PATCH /books/{id}`

Partial update (a convenience beyond the required routes): only the fields
present in the payload change.

```sh
curl -X PATCH localhost:8080/books/1 -d '{"year":1966}'
```

### `DELETE /books/{id}`

`204 No Content`, or `404` if it does not exist.

## Book representation

| Field    | Type            | Notes                                         |
| -------- | --------------- | --------------------------------------------- |
| `id`     | integer         | Assigned by the server                        |
| `title`  | string          | **Required**, non-blank, whitespace-trimmed   |
| `author` | string          | **Required**, non-blank, whitespace-trimmed   |
| `year`   | integer or null | Optional, 1–2200; numeric strings are accepted |
| `isbn`   | string or null  | Optional, up to 64 characters                 |

## Validation and status codes

| Status | When                                                              |
| ------ | ----------------------------------------------------------------- |
| `200`  | Successful read or update                                          |
| `201`  | Book created                                                       |
| `204`  | Book deleted                                                       |
| `400`  | Missing/blank `title` or `author`, bad field type, out-of-range `year`, non-numeric id, malformed or non-object JSON |
| `404`  | Unknown route, or no book with that id                             |
| `405`  | Known route, wrong method (includes an `Allow` header)             |
| `413`  | Request body over 4 MB                                             |
| `500`  | Unexpected storage failure                                         |

Validation failures list every problem at once:

```json
{
  "error": "validation failed",
  "status": 400,
  "details": ["title is required", "year must be an integer"]
}
```

Other errors use `{"error": "...", "status": n}`.

## Layout

```
src/
  Book.{h,m}          Model object and its JSON representation
  BookStore.{h,m}     SQLite persistence; all access serialised on a GCD queue
  HTTPMessage.{h,m}   HTTPRequest / HTTPResponse value types and serialisation
  HTTPServer.{h,m}    Socket accept loop, request parsing, connection handling
  BookRouter.{h,m}    Routing, payload validation, status-code mapping
  main.m              Argument parsing, wiring, signal handling
tests/
  TestSupport.{h,m}   Minimal block-based test harness
  HTTPTestClient.{h,m}Raw HTTP client used by the integration tests
  StoreTests.m        Storage layer
  RouterTests.m       Routing and validation, without sockets
  IntegrationTests.m  End-to-end over a real socket on an ephemeral port
```

### Design notes

- **Layering.** `BookRouter` depends on `BookStore` and the HTTP value types
  but not on the server, so routing and validation are tested directly, while
  `IntegrationTests` exercises the same code through a real socket.
- **Concurrency.** Each connection is handled on a concurrent GCD queue.
  `BookStore` funnels every statement through one serial queue, so a shared
  instance is safe; `HTTPServer`'s lifecycle flags are C11 atomics.
- **SQL injection.** Every value is bound as a parameter — never interpolated.
  A test asserts a `'); DROP TABLE books;--` title round-trips as data.
- **Connection handling.** One request per connection (`Connection: close`).
  Requests are capped at 64 KB of headers and 4 MB of body, and sockets carry
  send/receive timeouts so a stalled peer cannot pin a worker indefinitely.
