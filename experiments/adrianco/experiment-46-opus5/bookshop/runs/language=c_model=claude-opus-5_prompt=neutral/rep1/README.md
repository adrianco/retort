# bookapi

A REST API for managing a book collection, written in C with SQLite storage.

The HTTP server, the JSON reader and the JSON writer are all part of this
repository, so the only external dependency is `libsqlite3` — which ships with
macOS and is a single package on Linux.

## Requirements

- A C11 compiler (`clang` or `gcc`) and `make`
- `libsqlite3` plus its headers

```sh
# Debian / Ubuntu
sudo apt-get install build-essential libsqlite3-dev

# Fedora / RHEL
sudo dnf install gcc make sqlite-devel

# macOS — already present with the Xcode Command Line Tools
xcode-select --install
```

## Build and run

```sh
make            # builds build/bookapi
make run        # builds, then serves on 127.0.0.1:8080 using ./books.db
make test       # builds and runs all three test suites
make clean      # removes build artefacts and ./books.db
```

Running the binary directly:

```sh
./build/bookapi --port 8080 --db books.db
```

| Option | Env var | Default | Meaning |
| --- | --- | --- | --- |
| `--port N` | `PORT` | `8080` | TCP port; `0` asks the kernel for a free one |
| `--host ADDR` | `HOST` | `127.0.0.1` | IPv4 address to bind |
| `--db PATH` | `BOOKS_DB` | `books.db` | SQLite file, or `:memory:` |
| `-h`, `--help` | | | Print usage |

Command-line flags override environment variables. The server binds to loopback
by default so a development instance is not exposed to the network; pass
`--host 0.0.0.0` to change that deliberately. It creates the database file and
schema on first start, and shuts down cleanly on `SIGINT`/`SIGTERM`.

The startup line reports the port actually in use, which is what makes
`--port 0` practical:

```
bookapi: listening on http://127.0.0.1:8080 (db: books.db)
```

## API

All responses are JSON except `204 No Content`. Request bodies must be JSON
objects.

### `GET /health`

Verifies the service *and* its database — it runs a real query rather than
reporting a hollow `ok`, and answers `503` when storage is unreachable.

```json
{"status":"ok","database":"ok","books":2,"version":"1.0.0"}
```

### `POST /books`

Creates a book. Responds `201` with the stored record and a `Location` header.

```sh
curl -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-01359-3"}'
```

```json
{"id":1,"title":"Dune","author":"Frank Herbert","year":1965,
 "isbn":"9780441013593","created_at":"2024-05-01T10:00:00.123Z",
 "updated_at":"2024-05-01T10:00:00.123Z"}
```

### `GET /books` and `GET /books?author=NAME`

Lists books ordered by id. The `author` filter is an exact match but
case-insensitive, and returns an empty collection (not `404`) when nothing
matches.

```sh
curl localhost:8080/books
curl 'localhost:8080/books?author=frank%20herbert'
```

```json
{"count":1,"books":[{"id":1,"title":"Dune", "...": "..."}]}
```

### `GET /books/{id}`

Returns one book, or `404` if there is no such id.

### `PUT /books/{id}`

Replaces a book. `PUT` is a full replacement, so **omitting `year` or `isbn`
clears them** — send every field you want to keep.

```sh
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (Deluxe)","author":"Frank Herbert","year":1965}'
```

`created_at` is preserved; `updated_at` moves forward.

### `DELETE /books/{id}`

Removes a book and returns `204` with an empty body, or `404` if it was already
gone.

## Validation

| Field | Rules |
| --- | --- |
| `title` | **required**, string, trimmed, 1–512 characters |
| `author` | **required**, string, trimmed, 1–256 characters |
| `year` | optional, whole number between 1 and 2200; `null` clears it |
| `isbn` | optional, a valid ISBN-10 or ISBN-13; `null` or `""` clears it |

Notes on the less obvious choices:

- **ISBNs are checksum-verified and normalised.** Hyphens and spaces are
  stripped before storage, so `978-0-441-01359-3` and `9780441013593` are
  recognised as the same book. ISBNs are unique across the collection; a
  duplicate is a `409`.
- **Unknown fields are rejected**, so a typo like `"titel"` fails loudly
  instead of being silently dropped. The server-owned fields `id`,
  `created_at` and `updated_at` are accepted and ignored, which means a `GET`
  response can be edited and sent straight back as a `PUT`.
- Values are trimmed of surrounding whitespace, and a whitespace-only `title`
  counts as empty.

## Status codes

| Code | When |
| --- | --- |
| `200` | Successful `GET` or `PUT` |
| `201` | Book created |
| `204` | Book deleted |
| `400` | Body is not valid JSON, or the request is malformed |
| `404` | No such route or no such book |
| `405` | Known path, unsupported method (includes an `Allow` header) |
| `409` | The ISBN is already used by another book |
| `413` | Request body over 1 MiB |
| `422` | Valid JSON that fails validation |
| `500` | Unexpected server-side failure |
| `503` | The database is unreachable (from `/health`) |

Errors carry a stable machine-readable `error` code plus a human `message`:

```json
{"error":"not_found","message":"no book with id 42"}
```

Validation failures add a per-field breakdown:

```json
{"error":"validation_failed",
 "message":"the request body failed validation",
 "details":[{"field":"title","message":"is required"},
            {"field":"year","message":"must be between 1 and 2200"}]}
```

## Tests

```sh
make test
```

Three suites run in sequence, 276 checks in total:

| Suite | Covers |
| --- | --- |
| `tests/test_json.c` | The JSON parser and writer: escapes, surrogate pairs, number grammar, nesting limits, and a table of malformed inputs that must be rejected |
| `tests/test_db.c` | The storage layer against a real SQLite database (CRUD, author filtering, ISBN uniqueness, persistence across reopen) plus validation and serialisation rules |
| `tests/test_api.c` | End-to-end: it launches the actual `build/bookapi` binary on an ephemeral port and drives every endpoint over real TCP sockets, including error paths, `405`/`404` routing, split packets, and a server restart to prove data is durable |

The integration suite starts the server with `--port 0` and reads the chosen
port from its startup line, so test runs never collide on a fixed port and no
external HTTP client is required.

To run the suites under sanitizers:

```sh
make clean
make test CFLAGS="-std=c11 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer"
```

## Layout

```
src/strbuf.c      growable, always-NUL-terminated byte buffer
src/json.c        strict JSON parser + escaping writer
src/http.c        HTTP/1.1 request parsing, routing-agnostic accept loop
src/db.c          SQLite schema and CRUD, all statements parameter-bound
src/book_json.c   JSON <-> book translation and validation
src/api.c         endpoint routing and status-code policy
src/main.c        configuration, signal handling, startup
```

## Design notes

- **One request per connection.** Responses always carry `Connection: close`,
  which keeps the server small while staying within HTTP/1.1. Accepted sockets
  get send/receive timeouts so a stalled client cannot wedge the accept loop.
- **Single-threaded.** Requests are served sequentially, which suits a
  collection service of this size and removes a whole class of concurrency
  bugs. SQLite is opened in WAL mode with a busy timeout, so a second process
  can read the same file.
- **Every SQL statement is parameter-bound** — no query is built by string
  concatenation, and the test suites include injection attempts through both
  the author filter and the request body.
- **Untrusted input is bounded**: header block 16 KiB, body 1 MiB, path 1 KiB,
  JSON nesting 64 levels. Header values are checked for CR/LF before being
  written, and all strings are escaped on output, so response headers cannot be
  forged through stored data.
- **Internal errors are not leaked.** Database messages go to the log; the
  client gets a generic `500`.

### Known limitations

- IPv4 only, and `--host` takes an address literal rather than a hostname.
- Listing is unpaginated; a very large collection is returned in one response.
- `PUT` replaces the whole resource. There is no `PATCH` for partial updates.
- No authentication — this is intended to run on a trusted network or behind a
  proxy that terminates TLS and handles auth.
