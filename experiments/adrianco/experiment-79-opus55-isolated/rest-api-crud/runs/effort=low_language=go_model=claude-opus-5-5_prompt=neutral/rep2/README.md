# Books API

A small REST service for managing a book collection, written in Go with the
standard library `net/http` router and SQLite for storage
([modernc.org/sqlite](https://pkg.go.dev/modernc.org/sqlite), a pure-Go driver,
so no C compiler is needed).

## Setup

Requires Go 1.26 or newer (see `go.mod`).

```bash
go mod download
```

## Run

```bash
go run .
```

Configuration is by environment variable:

| Variable  | Default    | Meaning                     |
|-----------|------------|-----------------------------|
| `ADDR`    | `:8080`    | Listen address              |
| `DB_PATH` | `books.db` | SQLite database file to use |

## Test

```bash
go test ./...
```

The tests drive the HTTP handler against an in-memory SQLite database.

## API

A book looks like:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
```

| Method | Path          | Success          | Notes                                         |
|--------|---------------|------------------|-----------------------------------------------|
| GET    | `/health`     | 200              | `{"status":"ok"}`                             |
| POST   | `/books`      | 201 + book       | Sets a `Location` header                      |
| GET    | `/books`      | 200 + array      | `?author=` filters by exact author, any case  |
| GET    | `/books/{id}` | 200 + book       |                                               |
| PUT    | `/books/{id}` | 200 + book       | Full replacement; omitted fields are cleared  |
| DELETE | `/books/{id}` | 204, empty body  |                                               |

Validation: `title` and `author` are required (non-blank), and `year` must not
be negative. `year` and `isbn` are optional.

Errors are JSON, with per-field detail for validation failures:

```json
{"error": "validation failed", "fields": {"title": "title is required"}}
```

| Status | When                                                     |
|--------|----------------------------------------------------------|
| 400    | Malformed JSON, failed validation, or a non-numeric id   |
| 404    | No book with that id                                     |
| 405    | Method not supported on the path                         |
| 413    | Request body over 1 MB                                   |

## Example

```bash
curl -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'localhost:8080/books?author=Frank+Herbert'
curl -X PUT localhost:8080/books/1 \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:8080/books/1
```
