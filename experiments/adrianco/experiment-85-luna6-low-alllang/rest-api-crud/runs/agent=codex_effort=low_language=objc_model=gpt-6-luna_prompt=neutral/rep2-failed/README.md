# Objective-C Books API

A small HTTP JSON service for a SQLite-backed book collection, implemented with macOS Foundation and POSIX sockets.

## Build and run

Requires macOS with Xcode Command Line Tools.

```sh
make
./books-api             # listens on port 8080
./books-api 9000        # optional port
```

The service stores records in `books.sqlite` in the current directory. Set `BOOKS_DB=/path/to/file.sqlite` to choose another database.

## Routes

- `GET /health`
- `POST /books` with JSON `{ "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719" }`
- `GET /books` and `GET /books?author=Frank%20Herbert`
- `GET /books/{id}`
- `PUT /books/{id}` with the same JSON fields (title and author required)
- `DELETE /books/{id}`

Responses use JSON. Creation returns `201`, successful retrieval/update/deletion returns `200`, invalid data returns `400`, and unknown routes or IDs return `404`.

## Tests

Run `make tests` to compile and run the Objective-C integration checks against a temporary SQLite database.
