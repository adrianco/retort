# Books API

A REST API for managing a book collection, written in Go. It uses the standard
library's HTTP router and stores books in SQLite through
[modernc.org/sqlite](https://pkg.go.dev/modernc.org/sqlite), a pure-Go driver,
so you don't need a C compiler or CGO.

## Requirements

- Go 1.25 or newer

## Running

```sh
go run .
```

The server listens on port 8080 and stores books in `books.db` in the current
directory, creating the file on first run. It logs each request to standard
error. Stop it with Ctrl-C (or SIGTERM): it lets in-flight requests finish
before it exits.

To build and run a binary instead:

```sh
go build -o booksapi .
./booksapi -addr :9000 -db /var/lib/books/books.db
```

### Configuration

| Flag    | Environment variable        | Default    | Meaning                                                   |
|---------|-----------------------------|------------|-----------------------------------------------------------|
| `-addr` | `PORT` (listens on `:$PORT`) | `:8080`    | Address to listen on                                      |
| `-db`   | `DB_PATH`                   | `books.db` | SQLite database file, or `:memory:` for a throwaway database |

Flags take precedence over environment variables.

## Testing

```sh
go test ./...
go test -race ./...   # also checks for data races
```

The tests include:

- API tests that make real HTTP requests to the server, using a new SQLite
  database file for each test.
- Unit tests for input validation and the data layer.
- An end-to-end test that starts the server on a free port, uses it, and shuts
  it down.

## API

Request and response bodies are JSON. A book looks like this:

```json
{
  "id": 1,
  "title": "Nineteen Eighty-Four",
  "author": "George Orwell",
  "year": 1949,
  "isbn": "978-0-452-28423-4"
}
```

| Field    | Type            | Rules |
|----------|-----------------|-------|
| `id`     | integer         | Assigned by the server. The IDs of deleted books are never reused. |
| `title`  | string          | **Required.** Surrounding whitespace is trimmed. At most 500 characters. |
| `author` | string          | **Required.** Surrounding whitespace is trimmed. At most 255 characters. |
| `year`   | integer or null | Optional. From 1 to next year, so that forthcoming titles can be added. |
| `isbn`   | string or null  | Optional. An ISBN-10 or ISBN-13, which may contain hyphens or spaces; an ISBN-10 may end in `X`. Stored exactly as sent. Check digits aren't verified, because some real books have misprinted ISBNs. |

### Endpoints

| Request                  | Success response | Error responses |
|--------------------------|------------------|-----------------|
| `GET /health`            | `200` `{"status":"ok"}` | `503` `{"status":"unavailable"}` if the database can't be reached |
| `POST /books`            | `201` with the new book, and its URL in the `Location` header | `400` invalid input, `413` body larger than 1 MiB |
| `GET /books`             | `200` with an array of all books, in the order they were added | |
| `GET /books?author=text` | `200` with the books whose author contains `text` | |
| `GET /books/{id}`        | `200` with the book | `400` malformed ID, `404` no such book |
| `PUT /books/{id}`        | `200` with the updated book | `400` malformed ID or invalid input, `404` no such book, `413` body too large |
| `DELETE /books/{id}`     | `204` with no body | `400` malformed ID, `404` no such book |

Other methods on these paths get `405 Method Not Allowed` with an `Allow`
header, and unknown paths get `404`.

**PUT replaces the whole book.** Like POST, it requires `title` and `author`,
and it clears `year` or `isbn` if you leave them out. The API ignores fields it
doesn't recognize, including `id`, so you can fetch a book with GET, change
it, and send the whole thing back with PUT.

**The author filter** matches any part of the author's name and ignores case,
for accented and other non-ASCII letters too. For example, `?author=orwell`
finds "George Orwell" and `?author=émile` finds "Émile Zola". Surrounding
whitespace is ignored, and an empty value means no filter.

### Errors

Every error response contains an `error` message. When input fails
validation, `fields` also says what is wrong with each invalid field:

```json
{
  "error": "validation failed",
  "fields": {
    "author": "is required",
    "year": "must be between 1 and 2027"
  }
}
```

If something goes wrong on the server, the response is `500` with
`{"error":"internal server error"}`. The details go to the server log, not to
the client.

### Examples

```sh
# Create a book
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Nineteen Eighty-Four", "author": "George Orwell", "year": 1949, "isbn": "978-0-452-28423-4"}'

# List all books, or only those by a given author
curl localhost:8080/books
curl 'localhost:8080/books?author=orwell'

# Get a book
curl localhost:8080/books/1

# Replace a book (the ISBN is cleared because it is left out)
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "1984", "author": "George Orwell", "year": 1949}'

# Delete a book
curl -i -X DELETE localhost:8080/books/1

# Check health
curl localhost:8080/health
```

## Project layout

| File        | Contents |
|-------------|----------|
| `main.go`   | Configuration, startup and graceful shutdown |
| `server.go` | Routes, handlers, JSON encoding, error responses, request logging and panic recovery |
| `book.go`   | The `Book` type and input validation |
| `store.go`  | The SQLite schema and queries |
| `*_test.go` | Tests |
