# Books API (C)

A small REST service for managing a book collection, written in C11 with
POSIX sockets and SQLite. No third-party dependencies beyond `libsqlite3`.

## Requirements

- A C compiler (`cc`/clang/gcc) and `make`
- SQLite development library (preinstalled on macOS; `apt install libsqlite3-dev` on Debian/Ubuntu)

## Build, test, run

```sh
make            # builds build/books-api
make test       # builds and runs the test suite
./build/books-api
```

Configuration is via environment variables:

| Variable  | Default    | Meaning                  |
|-----------|------------|--------------------------|
| `PORT`    | `8080`     | TCP port to listen on    |
| `DB_PATH` | `books.db` | SQLite database file     |

## API

| Method | Path          | Success | Notes                                   |
|--------|---------------|---------|-----------------------------------------|
| GET    | `/health`     | 200     | `{"status":"ok"}`                       |
| POST   | `/books`      | 201     | Creates a book, returns it              |
| GET    | `/books`      | 200     | Lists books; `?author=` exact-match filter |
| GET    | `/books/{id}` | 200     |                                         |
| PUT    | `/books/{id}` | 200     | Full replacement; returns updated book  |
| DELETE | `/books/{id}` | 204     | No body                                 |

Book JSON: `{"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`

- `title` and `author` are required, non-blank strings.
- `year` (integer) and `isbn` (string) are optional and returned as `null` when absent.
- Errors are returned as `{"error":"..."}` with `400` (invalid JSON, validation
  failure, malformed id), `404` (unknown book or route), `405` (unsupported method),
  `413` (body over 1 MB).

```sh
curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl 'localhost:8080/books?author=Frank%20Herbert'
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune","author":"F. Herbert"}'
curl -X DELETE localhost:8080/books/1
```

## Layout

- `src/main.c` — HTTP server (single-threaded, one request per connection)
- `src/api.c` — routing, validation and SQLite access
- `src/json.c` — JSON request parsing and string escaping
- `tests/test_api.c` — integration tests against an in-memory database
