# Book API

A small Swift HTTP service for managing books, backed by SQLite.

## Requirements

- Swift 6.0 or newer
- SQLite development library (`sqlite3`; available with Xcode command line tools on macOS)

## Run

```sh
swift run BookAPI
```

The service listens on port `8080` and stores data in `books.sqlite` in the current directory. Set `PORT` and `DATABASE_PATH` to change these values:

```sh
PORT=9000 DATABASE_PATH=/tmp/books.sqlite swift run BookAPI
```

## API

- `GET /health` — returns `{"status":"ok"}`
- `POST /books` — create a book with JSON such as `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}` (returns `201`)
- `GET /books` — list books; add `?author=Frank%20Herbert` to filter by author
- `GET /books/{id}` — retrieve one book
- `PUT /books/{id}` — replace a book using the same JSON fields as create
- `DELETE /books/{id}` — delete a book (returns `204`)

Title and author are required and must not be blank. `year` and `isbn` are optional. Responses use JSON and missing book IDs return `404`.

## Tests

```sh
swift test
```
