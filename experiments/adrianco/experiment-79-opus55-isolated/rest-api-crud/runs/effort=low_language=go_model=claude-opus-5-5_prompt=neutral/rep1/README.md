# Books API

A small REST service for managing a book collection, written in Go with the
standard library `net/http` router and SQLite for storage
(`modernc.org/sqlite`, a pure-Go driver — no C compiler needed).

## Setup

Requires Go 1.22 or newer.

```bash
go mod download
```

## Run

```bash
go run .
```

Configuration is via environment variables:

| Variable  | Default    | Meaning                   |
|-----------|------------|---------------------------|
| `ADDR`    | `:8080`    | Listen address            |
| `DB_PATH` | `books.db` | SQLite database file path |

## Test

```bash
go test ./...
```

Tests run against an in-memory SQLite database (plus one that checks data
survives reopening a database file).

## API

A book looks like:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
```

| Method | Path          | Success          | Errors                        |
|--------|---------------|------------------|-------------------------------|
| GET    | `/health`     | 200 `{"status":"ok"}` | 503 if the database is down |
| POST   | `/books`      | 201 + the book, `Location` header | 400 invalid body |
| GET    | `/books`      | 200 + array      |                               |
| GET    | `/books/{id}` | 200 + the book   | 400 bad id, 404 not found     |
| PUT    | `/books/{id}` | 200 + the book   | 400 bad id/body, 404 not found |
| DELETE | `/books/{id}` | 204, empty body  | 400 bad id, 404 not found     |

- `GET /books?author=Frank+Herbert` filters by author (exact match, case-insensitive).
- `title` and `author` are required and must not be blank; `year` must not be
  negative. `year` and `isbn` are optional.
- `PUT` replaces the whole book, so omitted optional fields are reset.
- Errors are JSON: `{"error": "..."}`; validation failures add a `details`
  array listing each problem.

## Example

```bash
curl -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl localhost:8080/books
curl 'localhost:8080/books?author=Frank+Herbert'
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:8080/books/1
```
