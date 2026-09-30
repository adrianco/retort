# Book Collection API

A small REST API for managing a collection of books, written in Go. It uses only
the standard library's `net/http` for routing and stores its data in SQLite.

## Requirements

- Go 1.25 or newer.
- Network access the first time you build, so Go can download the SQLite driver.

The SQLite driver ([`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite))
is pure Go: no C compiler or system SQLite library is needed.

Platforms: developed and tested on macOS. The build also cross-compiles for
Linux (amd64, arm64), but the tests have not been run there, and Windows has
not been tried.

## Quick start

```sh
go run .
```

The server listens on `http://localhost:8080` and keeps its data in `books.db`
in the current directory (created on first start). Check that it is up:

```sh
curl http://localhost:8080/health
# {"status":"ok"}
```

To build a standalone binary instead:

```sh
go build -o bookapi .
./bookapi
```

Stop the server with Ctrl-C (or SIGTERM). It finishes in-flight requests, for up
to 15 seconds, before exiting; a second Ctrl-C exits at once.

## Configuration

Flags take precedence over environment variables, which take precedence over the
defaults.

| Flag    | Environment          | Default    | Meaning                                                          |
|---------|----------------------|------------|------------------------------------------------------------------|
| `-addr` | `ADDR`, or `PORT`    | `:8080`    | Address to listen on. `PORT=9000` is shorthand for `ADDR=:9000`. |
| `-db`   | `DB_PATH`            | `books.db` | SQLite database file. `:memory:` gives a throwaway database.     |

```sh
go run . -addr 127.0.0.1:9000 -db /var/lib/books/books.db   # loopback only
PORT=9000 go run .
go run . -db :memory:                                        # data is lost on exit
```

The directory that holds the database file must already exist, and an empty
`-addr` or `-db` is rejected. Run `go run . -h` for the flag summary.

## API

All request and response bodies are JSON.

| Method   | Path           | Description                               | Success                     |
|----------|----------------|-------------------------------------------|-----------------------------|
| `POST`   | `/books`       | Create a book                             | `201 Created`               |
| `GET`    | `/books`       | List books; filter with `?author=`        | `200 OK`                    |
| `GET`    | `/books/{id}`  | Get one book                              | `200 OK`                    |
| `PUT`    | `/books/{id}`  | Replace a book                            | `200 OK`                    |
| `DELETE` | `/books/{id}`  | Delete a book                             | `204 No Content`            |
| `GET`    | `/health`      | Health check: reads the `books` table     | `200 OK` / `503` if it fails |

### The book resource

```json
{
  "id": 1,
  "title": "The Go Programming Language",
  "author": "Alan Donovan",
  "year": 2015,
  "isbn": "9780134190440"
}
```

| Field    | Type    | Required | Rules                                                          |
|----------|---------|----------|----------------------------------------------------------------|
| `id`     | integer | -        | Assigned by the server; never reused after a delete. In a URL it is written without a sign or leading zeros. |
| `title`  | string  | **yes**  | Not blank (white space and zero-width characters such as U+200B do not count), at most 255 characters. |
| `author` | string  | **yes**  | Not blank (same rule), at most 255 characters.                 |
| `year`   | integer | no       | 0 to 9999. `0` (also the default) means "unknown".             |
| `isbn`   | string  | no       | At most 32 characters. Free-form: the checksum is not checked. |

Other behaviour worth knowing:

- Surrounding whitespace (newlines and tabs included) is trimmed from `title`,
  `author` and `isbn`. Control characters anywhere else in those fields are
  rejected.
- A missing optional field reads back as its zero value: `"year": 0`, `"isbn": ""`.
- Unknown JSON fields are ignored, including an `id` in the body: the server
  assigns ids on `POST`, and on `PUT` the id in the URL is the one that counts.
- `Content-Type` is not enforced, so `curl -d '{...}'` works without a header.
  Request bodies are limited to 1 MiB.
- `PUT` replaces the whole book, as HTTP defines it. `title` and `author` are
  required again, and optional fields you leave out are reset to unknown. There
  is no partial update.
- `GET /books` returns books in id order, as a bare JSON array (`[]` when there
  are none).
- `?author=` matches the whole author name, compared case-insensitively (SQLite's
  `NOCASE`, which folds ASCII letters only). It does not match part of a name, and
  a blank value means no filter. A malformed query string on this endpoint, a
  stray `%` or a `;` anywhere in it (even in an unrelated parameter), is a `400`
  rather than being silently ignored.

### Examples

```sh
# Create
curl -i -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Nineteen Eighty-Four","author":"George Orwell","year":1949}'
# HTTP/1.1 201 Created
# Location: /books/1
# {"id":1,"title":"Nineteen Eighty-Four","author":"George Orwell","year":1949,"isbn":""}

# List everything, or only one author's books
curl http://localhost:8080/books
curl 'http://localhost:8080/books?author=george%20orwell'

# Get one
curl http://localhost:8080/books/1

# Replace (send every field you want to keep)
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"1984","author":"George Orwell","year":1949,"isbn":"9780451524935"}'
# {"id":1,"title":"1984","author":"George Orwell","year":1949,"isbn":"9780451524935"}

# Delete (204 No Content, empty body)
curl -i -X DELETE http://localhost:8080/books/1
```

### Errors

Every error the API produces is JSON with an `error` message. Validation
failures also list each rejected field under `details`:

```sh
curl -s -X POST http://localhost:8080/books -d '{"title":"   "}'
```

```json
{
  "error": "title is required; author is required",
  "details": [
    {"field": "title", "message": "is required"},
    {"field": "author", "message": "is required"}
  ]
}
```

| Status                         | When                                                                                  |
|--------------------------------|---------------------------------------------------------------------------------------|
| `400 Bad Request`              | Validation failed; malformed JSON or query string; a wrongly typed field; `{id}` not a positive integer without sign or leading zeros |
| `404 Not Found`                | No book with that id, or no such route                                                |
| `405 Method Not Allowed`       | The path exists but not for this method; the `Allow` header lists what does           |
| `413 Request Entity Too Large` | Body over 1 MiB                                                                       |
| `500 Internal Server Error`    | Unexpected failure. The details are logged, never sent to the client                  |
| `499` (non-standard, from nginx) | The client went away, or closed its sending side, before a read could be answered. Nobody sees it; it mostly shows up in the log |
| `503 Service Unavailable`      | `GET /health`: the `books` table could not be read within 2 seconds. Any endpoint: the request waited more than 8 seconds for its turn at the database |

A few failures never reach the API and are answered by Go's HTTP server itself,
in plain text or as a redirect rather than JSON: a malformed request line or
percent-escape in the path, a request without a `Host` header, and non-canonical
paths such as `//books` or `/books/../health`, which get a `307` to the clean
path.

## Tests

```sh
go test ./...            # everything
go test -race ./...      # with the race detector
go test -cover ./...     # with coverage

# optional: keep fuzzing beyond the built-in seed inputs
go test -run '^$' -fuzz FuzzCreateBookBody -fuzztime 30s ./internal/api   # request bodies
go test -run '^$' -fuzz FuzzRequestTarget  -fuzztime 30s ./internal/api   # paths and query strings
```

The tests use no network beyond the loopback interface and need no setup. They
run against real SQLite databases in temporary directories, not mocks; the only
fakes are fault injectors (a store that fails or panics on demand, a request
body or response writer that errors) to check that faults never leak to clients.

| Package             | What is covered                                                                                                                        |
|---------------------|----------------------------------------------------------------------------------------------------------------------------------------|
| `internal/book`     | Validation rules and normalization.                                                                                                    |
| `internal/store`    | CRUD against file and in-memory databases, author filter, id stability, persistence across reopen, concurrent writers, lock waiting, unusual file paths, SQL-injection inertness, and the health check noticing a dropped table or a damaged file. |
| `internal/api`      | Every endpoint and status code end to end, validation and malformed-input handling, id and query-string strictness, the body-size limit, 404/405 JSON, hidden 500s, requests from clients that have gone, slow-database 503s, panic recovery, logging, and two fuzz tests: no request body, path or query string may cause a 5xx, and everything accepted must be valid. |
| `main` (repository root) | Flag/environment precedence; `main()` itself as a child process (exit codes, SIGINT/SIGTERM handling); then the real service on a TCP port: requests, half-closing clients, graceful shutdown that lets an in-flight request finish, server timeouts, and data surviving a restart. |

## Project layout

```
main.go                 flags/environment, wiring, graceful shutdown
internal/book/          Book type, validation rules, ErrNotFound
internal/store/         SQLite persistence (implements api.BookStore)
internal/api/           HTTP handlers, JSON helpers, middleware
```

`internal/api` depends on a small `BookStore` interface rather than on SQLite,
so the persistence layer can be swapped or faked without touching the handlers.

## Design notes

- **No framework.** Go 1.22's `net/http` routing understands method-and-path
  patterns such as `GET /books/{id}`, which is all this API needs.
- **One SQLite connection.** SQLite allows a single writer at a time, so the
  store funnels all access through one connection. That avoids "database is
  locked" errors between pooled connections and keeps `:memory:` databases
  (private to their connection) coherent. A busy timeout also makes it wait, up
  to 5 seconds, rather than fail at once if another process such as the
  `sqlite3` shell holds a lock; if the lock is still held after that, the
  request fails with a `500`.
- **JSON responses.** Even 404s for unknown routes and 405s are JSON, and
  unexpected failures are logged with their details but reported to the client
  only as `internal server error`.
- **Request logging** goes to standard error through `log/slog`, one line per
  request, at error level for 5xx responses.
- **Disconnected clients.** Reads are abandoned as soon as the client goes away,
  so departed clients cannot keep the database busy; the log shows them as
  status `499`. Writes are not: once a write has reached the database it always
  finishes, because cancelling it while it commits could leave the response and
  the log claiming the opposite of what happened to the book. A `201` therefore
  really does mean the book was stored. Go also treats a client that merely
  closes its sending side after writing its request (as some simple tools do) as
  gone: its writes are still carried out, but its reads are normally answered
  with `499`. A request waits at most 8 seconds for its turn at the database, and
  a write can then wait the lock time described above, so the server allows 15
  seconds before it gives up on writing a response.
- **Health check.** `/health` runs a small query against the `books` table. It
  shares the store's single connection, so under heavy load, or while a write is
  stuck waiting for a lock held by another process, it can answer `503` after 2
  seconds even though the database is intact.
- **Trusted use only.** There is no authentication and no CORS handling, and
  `Content-Type` is not checked (so a web page in a browser could still create
  a book with a cross-site form post). Run it on a trusted network or behind a
  proxy, and bind it to loopback (`-addr 127.0.0.1:8080`) for local use.
