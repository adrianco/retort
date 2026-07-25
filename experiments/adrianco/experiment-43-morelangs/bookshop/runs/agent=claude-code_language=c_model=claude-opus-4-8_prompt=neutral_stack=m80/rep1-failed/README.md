# Book Collection API (C)

A small REST API for managing a book collection, written in C with no
third-party frameworks. It uses the POSIX sockets API for HTTP and **SQLite**
for storage. JSON parsing/serialization is a compact self-contained module.

## Requirements

- A C11 compiler (`cc` / `clang` / `gcc`)
- `make`
- SQLite development library (`-lsqlite3`)
  - macOS: available in the system SDK — nothing to install.
  - Debian/Ubuntu: `sudo apt-get install libsqlite3-dev`
- `curl` and `bash` (only for the HTTP integration test)

## Build

```sh
make            # builds the ./bookapi server binary
```

## Run

```sh
./bookapi                    # listens on :8080, data in ./books.db
./bookapi --port 9000        # custom port
./bookapi --db /tmp/my.db    # custom database file
```

The server prints the listen address on startup and stores data in an SQLite
file that persists across restarts.

## API

All responses are JSON. Bodies for `POST`/`PUT` must be a JSON object.

| Method | Path            | Description                        | Success |
|--------|-----------------|------------------------------------|---------|
| GET    | `/health`       | Health check                       | 200     |
| POST   | `/books`        | Create a book                      | 201     |
| GET    | `/books`        | List books (`?author=` filter)     | 200     |
| GET    | `/books/{id}`   | Get one book                       | 200     |
| PUT    | `/books/{id}`   | Replace a book                     | 200     |
| DELETE | `/books/{id}`   | Delete a book                      | 204     |

### Book fields

| Field    | Type            | Required | Notes                     |
|----------|-----------------|----------|---------------------------|
| `title`  | string          | yes      | non-empty                 |
| `author` | string          | yes      | non-empty                 |
| `year`   | integer or null | no       | publication year          |
| `isbn`   | string or null  | no       |                           |

### Status codes

- `200 OK` — successful GET/PUT
- `201 Created` — successful POST (returns the created book)
- `204 No Content` — successful DELETE
- `400 Bad Request` — missing/empty `title` or `author`, or malformed JSON
- `404 Not Found` — unknown route or missing book id
- `405 Method Not Allowed` — unsupported method for a known path
- `500 Internal Server Error` — database failure

Error responses have the shape `{"error":"...message..."}`.

## Examples

```sh
# Create
curl -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Herbert","year":1965,"isbn":"0441172717"}'
# -> 201 {"id":1,"title":"Dune","author":"Herbert","year":1965,"isbn":"0441172717"}

# List, and filter by author
curl localhost:8080/books
curl 'localhost:8080/books?author=Herbert'

# Get one
curl localhost:8080/books/1

# Update
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Herbert","year":1969}'

# Delete
curl -X DELETE localhost:8080/books/1   # -> 204

# Health
curl localhost:8080/health              # -> {"status":"ok"}
```

## Tests

Two independent test suites:

```sh
make test          # C integration tests: drives the request handler against
                   # an in-memory SQLite DB (no network). 33 assertions.

make integration   # HTTP-level tests: starts the server and hits every
                   # endpoint with curl. 12 assertions.
```

`make test` exercises the full parse → validate → persist → serialize path
covering creation, retrieval, listing, the `?author=` filter (including
URL-decoding), updates, deletes, validation failures, and 404/405 handling.

## Source layout

| File            | Responsibility                                        |
|-----------------|-------------------------------------------------------|
| `main.c`        | Socket accept loop + HTTP request/response framing    |
| `api.c` / `.h`  | Routing and request handling (transport-independent)  |
| `db.c` / `.h`   | SQLite schema and CRUD data access                    |
| `json.c` / `.h` | Minimal flat-object JSON parser                        |
| `strbuf.c`/`.h` | Growable string buffer + JSON string escaping         |
| `test_api.c`    | In-process integration tests                          |
| `test_integration.sh` | End-to-end HTTP tests via curl                  |

The API logic in `api.c` is deliberately separated from the socket code in
`main.c`, so it can be tested directly and reused behind a different transport.
