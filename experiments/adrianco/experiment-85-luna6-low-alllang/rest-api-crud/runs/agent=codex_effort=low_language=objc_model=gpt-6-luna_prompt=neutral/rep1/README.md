# Objective-C Book Collection API

A small REST API built with Objective-C Foundation and SQLite. The server uses only macOS system frameworks and SQLite; no package manager is needed.

## Build and run

Requirements: macOS with Xcode Command Line Tools, `clang`, and `curl` (for integration tests).

```sh
./build.sh
./books-server --port 8080 --db ./books.sqlite
```

The database file is created when the server starts. `--port` and `--db` are optional; defaults are `8080` and `books.sqlite` in the current directory.

## API

All request and response bodies use JSON. `title` and `author` must be nonempty strings. `year` and `isbn` are optional.

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/health` | Returns `{"status":"ok"}` |
| POST | `/books` | Creates a book; returns `201` and the new record |
| GET | `/books` | Lists all books; optional exact-match `?author=...` filter |
| GET | `/books/{id}` | Returns one book or `404` |
| PUT | `/books/{id}` | Replaces title, author, year, and isbn; returns updated record or `404` |
| DELETE | `/books/{id}` | Deletes a book; returns `{"deleted":true}` or `404` |

Example:

```sh
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'http://localhost:8080/books?author=Frank%20Herbert'
```

Malformed JSON and requests missing a valid title or author receive `400`. Unknown paths and missing book IDs receive `404`.

## Tests

```sh
./unit-tests.sh      # SQLite create, read, filter, update, delete checks
./Tests.sh           # HTTP integration tests (requires permission to bind a local socket)
```
