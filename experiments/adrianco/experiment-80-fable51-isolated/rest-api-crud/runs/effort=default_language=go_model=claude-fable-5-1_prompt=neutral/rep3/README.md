# Book Collection API

A REST API for managing a book collection, written in Go with the standard
library `net/http` router and SQLite for storage (via the pure-Go
`modernc.org/sqlite` driver, so no C compiler is needed).

## Setup and run

Requires Go 1.26 or newer (see `go.mod`).

```bash
go mod download
go run .
```

The server listens on `:8080` and stores data in `books.db` in the current
directory. Both are configurable through environment variables:

| Variable  | Default    | Description                                      |
|-----------|------------|--------------------------------------------------|
| `ADDR`    | `:8080`    | Listen address                                   |
| `DB_PATH` | `books.db` | SQLite database file (`:memory:` for ephemeral)  |

To build a binary instead: `go build -o bookapi . && ./bookapi`

## Tests

```bash
go test ./...
```

The tests run the full HTTP handler against an in-memory SQLite database.

## API

A book looks like this:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

| Method | Path          | Description                                   | Success          |
|--------|---------------|-----------------------------------------------|------------------|
| GET    | `/health`     | Health check                                  | `200`            |
| POST   | `/books`      | Create a book                                 | `201` + the book |
| GET    | `/books`      | List books; `?author=` filters by author      | `200` + array    |
| GET    | `/books/{id}` | Get one book                                  | `200` + the book |
| PUT    | `/books/{id}` | Replace a book                                | `200` + the book |
| DELETE | `/books/{id}` | Delete a book                                 | `204`            |

Behaviour notes:

- `title` and `author` are required and must not be blank; `year` and `isbn`
  are optional (`year` must not be negative).
- `PUT` replaces the whole book, so it takes the same body as `POST`; omitted
  optional fields are reset to their defaults.
- The `?author=` filter is an exact, case-insensitive match.

Errors are JSON with an `error` message:

| Status | When                                                          |
|--------|---------------------------------------------------------------|
| `400`  | Malformed JSON, wrong field type, unknown field, or bad ID    |
| `404`  | No book with that ID                                          |
| `422`  | Validation failed; a `fields` object gives per-field messages |

### Examples

```bash
curl -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl localhost:8080/books
curl 'localhost:8080/books?author=Frank+Herbert'
curl localhost:8080/books/1

curl -X PUT localhost:8080/books/1 \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966,"isbn":"9780441172719"}'

curl -X DELETE localhost:8080/books/1
curl localhost:8080/health
```
