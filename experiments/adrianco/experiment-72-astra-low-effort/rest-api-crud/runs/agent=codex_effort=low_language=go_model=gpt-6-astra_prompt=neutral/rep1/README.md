# Book collection API

A Go REST service using `net/http` and a persistent SQLite database.

## Setup and run

Requires Go 1.22 or newer and a C compiler (the SQLite driver uses CGO).

```sh
go mod download
go build -o books .
./books
```

The service listens on `:8080` and creates `books.db` in the working directory.
Set `ADDR` and `DB_PATH` to override these defaults:

```sh
ADDR=127.0.0.1:9000 DB_PATH=collection.db go run .
```

## API

| Method | Path | Result |
| --- | --- | --- |
| POST | `/books` | Create; 201 with book and Location header |
| GET | `/books` | List in ID order; 200 with JSON array |
| GET | `/books?author=Frank%20Herbert` | Exact, case-sensitive author filter |
| GET | `/books/{id}` | Read book; 200 or 404 |
| PUT | `/books/{id}` | Replace book fields; 200 or 404 |
| DELETE | `/books/{id}` | Delete; 204 with no body or 404 |
| GET | `/health` | 200 with `{"status":"ok"}`; 503 if database unavailable |

```sh
curl -i -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl http://localhost:8080/books/1
```

POST and PUT require a JSON object with nonblank string `title` and `author`.
Surrounding whitespace is trimmed from those fields. Optional `year` is an
integer (defaults to 0); optional `isbn` is a string (defaults to empty).
PUT replaces all editable fields, so omitted optional fields reset to defaults.
IDs are assigned by the database and cannot be supplied in request bodies.
Unknown fields, malformed JSON, and invalid field types return 400. Bodies are
limited to 1 MiB (413). Invalid IDs return 400; missing resources return 404;
unsupported methods return 405 with an Allow header. Errors are JSON objects
with an `error` string. An empty list is `[]`.

## Tests

```sh
go test ./...
go test -race ./...
```

Tests use isolated temporary SQLite files and cover CRUD, filtering, validation,
HTTP errors, health checks, and persistence across database reopening.
