# Book Collection API

A small REST API for managing a book collection, written in Go with the
standard library `net/http` router and SQLite for storage.

The SQLite driver is [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite),
a pure-Go implementation, so no C compiler or system SQLite library is needed.

## Requirements

- Go 1.26 or newer (the version declared in `go.mod`)

## Setup and run

```bash
go mod download
go run .
```

The server listens on `http://localhost:8080` and stores data in `books.db` in
the current directory (created on first start).

| Variable   | Default    | Purpose                                          |
|------------|------------|--------------------------------------------------|
| `PORT`     | `8080`     | TCP port to listen on                            |
| `BOOKS_DB` | `books.db` | SQLite database path (`:memory:` for ephemeral)  |

```bash
PORT=9000 BOOKS_DB=/tmp/books.db go run .
```

To build a binary instead: `go build -o bookapi . && ./bookapi`

## Tests

```bash
go test ./...
```

The tests drive the HTTP handlers end to end against an in-memory SQLite
database; nothing is written to disk except in a temporary directory.

## API

A book looks like this:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
```

| Method | Path          | Description        | Success | Errors   |
|--------|---------------|--------------------|---------|----------|
| GET    | `/health`     | Health check       | 200     | 503      |
| POST   | `/books`      | Create a book      | 201     | 400      |
| GET    | `/books`      | List books         | 200     |          |
| GET    | `/books/{id}` | Get one book       | 200     | 400, 404 |
| PUT    | `/books/{id}` | Replace a book     | 200     | 400, 404 |
| DELETE | `/books/{id}` | Delete a book      | 204     | 400, 404 |

Behaviour worth knowing:

- `title` and `author` are required and must not be blank. `year` and `isbn`
  are optional and default to `0` and `""`; `year` must not be negative.
  Leading and trailing whitespace is trimmed from string fields.
- `GET /books?author=Jane+Austen` returns only books by that author. The match
  is on the whole author name and ignores case.
- `PUT` replaces the whole book, so omitted optional fields are reset to their
  defaults.
- `POST` responds with a `Location` header pointing at the new book.
- An `id` that is not a positive integer gets a 400; one that does not exist
  gets a 404.

Errors are JSON. Validation failures list the offending fields:

```json
{"error": "validation failed", "details": {"title": "title is required"}}
```

### Examples

```bash
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl localhost:8080/books
curl 'localhost:8080/books?author=Frank+Herbert'
curl localhost:8080/books/1

curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'

curl -i -X DELETE localhost:8080/books/1
curl localhost:8080/health
```
