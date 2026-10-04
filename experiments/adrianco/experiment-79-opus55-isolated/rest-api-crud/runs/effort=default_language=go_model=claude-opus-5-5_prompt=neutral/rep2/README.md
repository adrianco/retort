# Books API

A REST API for managing a book collection, written in Go with the standard
library `net/http` router and SQLite for storage.

## Requirements

- Go 1.26 or newer (the version declared in `go.mod`)

SQLite is provided by [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite),
a pure-Go driver, so no C compiler or system SQLite library is needed.

## Setup and run

```sh
go mod download
go run .
```

The server listens on `:8080` and stores data in `books.db` in the current
directory. Both are configurable through environment variables:

| Variable   | Default    | Description                                        |
|------------|------------|----------------------------------------------------|
| `PORT`     | `8080`     | TCP port to listen on                              |
| `BOOKS_DB` | `books.db` | SQLite database file (`:memory:` for non-persistent) |

```sh
PORT=9000 BOOKS_DB=/tmp/books.db go run .
```

To build a binary instead: `go build -o books . && ./books`

## Tests

```sh
go test ./...
```

The tests drive the HTTP handler against an in-memory SQLite database, plus one
test that checks data survives reopening a database file.

## API

A book looks like this:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
```

| Method | Path          | Description               | Success | Errors   |
|--------|---------------|---------------------------|---------|----------|
| GET    | `/health`     | Health check              | 200     | 503      |
| POST   | `/books`      | Create a book             | 201     | 400      |
| GET    | `/books`      | List books                | 200     |          |
| GET    | `/books/{id}` | Get one book              | 200     | 400, 404 |
| PUT    | `/books/{id}` | Replace a book            | 200     | 400, 404 |
| DELETE | `/books/{id}` | Delete a book (empty body) | 204     | 400, 404 |

Behaviour worth knowing:

- `title` and `author` are required and must not be blank. `year` and `isbn`
  are optional and default to `0` and `""`; `year` must not be negative.
- `PUT` replaces the whole book, so omitted optional fields are reset to their
  defaults.
- `GET /books?author=` matches the full author name, ignoring case
  (`?author=frank%20herbert` finds books by "Frank Herbert"; `?author=Frank`
  does not).
- A non-numeric or non-positive `{id}` returns 400; an unknown one returns 404.

Errors are returned as JSON. Validation failures list each offending field:

```json
{"error": "validation failed", "fields": {"title": "title is required"}}
```

### Examples

```sh
curl -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl localhost:8080/books
curl 'localhost:8080/books?author=Frank%20Herbert'
curl localhost:8080/books/1

curl -X PUT localhost:8080/books/1 \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"0441013597"}'

curl -X DELETE localhost:8080/books/1
curl localhost:8080/health
```
