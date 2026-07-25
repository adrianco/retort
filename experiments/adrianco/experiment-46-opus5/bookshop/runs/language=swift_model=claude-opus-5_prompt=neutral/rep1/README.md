# Book Collection API

A small REST API for managing a book collection, written in Swift with
[Vapor](https://vapor.codes) and [Fluent](https://docs.vapor.codes/fluent/overview/)
on an embedded SQLite database.

## Requirements

- Swift 5.9 or newer (developed against Swift 6.3)
- macOS 13+ or Linux
- Xcode (macOS only, **for running the tests** — see [Testing](#testing))

## Setup

```bash
swift build
```

The first build downloads and compiles Vapor and its dependencies, so expect a
few minutes. Subsequent builds are fast.

## Running

```bash
swift run App serve --hostname 127.0.0.1 --port 8080
```

The server listens on `http://127.0.0.1:8080`. The SQLite schema is created
automatically on startup.

| Environment variable | Default     | Purpose                       |
| -------------------- | ----------- | ----------------------------- |
| `DATABASE_PATH`      | `db.sqlite` | Location of the SQLite file   |

```bash
DATABASE_PATH=/var/lib/books.sqlite swift run App serve --port 8080
```

For a production build, use `swift build -c release` and run
`./.build/release/App serve`.

## Testing

```bash
./run-tests.sh
```

26 tests cover the endpoints end to end (real HTTP requests against a real
SQLite database) plus the validation rules in isolation.

> **macOS note:** `swift test` needs the `XCTest` framework, which ships with
> Xcode and *not* with the Command Line Tools. If `xcode-select -p` points at
> `/Library/Developer/CommandLineTools`, plain `swift test` fails with
> `no such module 'XCTest'`. `run-tests.sh` detects this and points
> `DEVELOPER_DIR` at an installed Xcode for that run only — it does not change
> any system setting. The equivalent one-liner:
>
> ```bash
> DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift test
> ```
>
> On Linux, or with Xcode already selected, plain `swift test` works.

Each test gets its own throwaway database file in the system temp directory, so
tests are isolated and leave nothing behind.

## API

All request and response bodies are JSON. `POST` and `PUT` require a
`Content-Type: application/json` header. Unknown fields in a request body are
ignored.

### `GET /health`

Reports service and database availability.

```bash
curl http://127.0.0.1:8080/health
```

```json
{ "database": "ok", "status": "ok" }
```

Returns `200 OK` when the database responds, `503 Service Unavailable`
otherwise.

### `POST /books`

Creates a book. Returns `201 Created`, the created book, and a `Location`
header pointing at it.

```bash
curl -X POST http://127.0.0.1:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"978-0-261-10221-7"}'
```

```json
{
  "author": "J.R.R. Tolkien",
  "createdAt": "2026-07-24T21:24:18Z",
  "id": "EFB77EA5-3ACB-4AEF-9B30-C63C9BE5BE0E",
  "isbn": "978-0-261-10221-7",
  "title": "The Hobbit",
  "updatedAt": "2026-07-24T21:24:18Z",
  "year": 1937
}
```

### `GET /books`

Lists every book, sorted by title then author. Returns `200 OK` with a JSON
array (`[]` when empty).

```bash
curl http://127.0.0.1:8080/books
curl 'http://127.0.0.1:8080/books?author=tolkien'
```

The optional `?author=` filter is a **case-insensitive partial match**, so
`?author=tolkien` matches `J.R.R. Tolkien`. A blank value is ignored and
returns everything.

### `GET /books/{id}`

Returns a single book (`200 OK`), `404 Not Found` if no book has that id, or
`400 Bad Request` if `{id}` is not a UUID.

### `PUT /books/{id}`

Replaces a book. `title` and `author` are required, exactly as for `POST`.
Following replace semantics, **omitting `year` or `isbn` clears them** — send
their current values to keep them. Returns `200 OK` with the updated book, or
`404 Not Found`.

```bash
curl -X PUT http://127.0.0.1:8080/books/$ID \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
```

### `DELETE /books/{id}`

Deletes a book. Returns `204 No Content` with an empty body, or `404 Not Found`
if it does not exist (deleting twice is a `404`, not a silent success).

## Book fields

| Field       | Type            | Notes                                                     |
| ----------- | --------------- | --------------------------------------------------------- |
| `id`        | UUID            | Server-assigned, read-only                                 |
| `title`     | string          | **Required**, trimmed, 1–512 characters                    |
| `author`    | string          | **Required**, trimmed, 1–512 characters                    |
| `year`      | integer \| null | Optional; between 1000 and next year                       |
| `isbn`      | string \| null  | Optional; 10 or 13 characters ignoring hyphens and spaces  |
| `createdAt` | ISO-8601 \| null| Server-assigned, read-only                                 |
| `updatedAt` | ISO-8601 \| null| Server-assigned, read-only                                 |

Optional fields are always present in responses, as `null` when unset, so the
response shape is stable. Unknown fields in a request body are ignored.

## Validation and errors

`title` and `author` are required and must be non-empty after trimming. `year`
and `isbn`, when supplied, must be well-formed; an empty `isbn` string clears
the field. The ISBN check validates shape only, not the check digit.

Failures return a JSON error body. All problems with a payload are reported in
one response:

```bash
curl -X POST http://127.0.0.1:8080/books \
  -H 'Content-Type: application/json' -d '{"year":42,"isbn":"nope"}'
```

```json
{
  "error": true,
  "reason": "'title' is required and must not be empty; 'author' is required and must not be empty; 'year' must be between 1000 and 2027; 'isbn' must be a valid 10 or 13 character ISBN"
}
```

| Status                    | When                                              |
| ------------------------- | ------------------------------------------------- |
| `200 OK`                  | Successful read or update                         |
| `201 Created`             | Book created                                      |
| `204 No Content`          | Book deleted                                      |
| `400 Bad Request`         | Validation failure, malformed JSON, or bad UUID   |
| `404 Not Found`           | No book with that id                              |
| `503 Service Unavailable` | Health check could not reach the database         |

A request sent without a JSON `Content-Type` is read as an empty body, so it
fails validation with `400` rather than being partially applied.

## Project layout

```
Sources/App/
  entrypoint.swift              @main — boots the Application
  configure.swift               JSON coders, SQLite, migrations, routes
  routes.swift                  Route registration
  Models/Book.swift             Fluent model for the books table
  Migrations/CreateBook.swift   Schema migration
  DTOs/BookDTOs.swift           Request/response types and validation rules
  Controllers/
    BookController.swift        CRUD handlers for /books
    HealthController.swift      /health handler
Tests/AppTests/
  BookAPITests.swift            End-to-end tests for every endpoint
  BookValidationTests.swift     Unit tests for the validation rules
  HealthTests.swift             Health check test
  TestHelpers.swift             Application lifecycle and request helpers
```
