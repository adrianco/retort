# Book Collection API

A Rust REST API built with Axum and SQLite.

## Setup and run

Install a current stable Rust toolchain with Cargo and a C compiler for the bundled SQLite library. From this directory, run:

```sh
cargo build --locked
cargo test --locked
cargo run --locked
```

The service listens on `127.0.0.1:3000` by default and creates `books.db` in the working directory. Set `BOOKS_ADDR` to change the bind address and `BOOKS_DB` to change the database file path. The service initializes the table automatically.

## API

| Method | Path | Successful response |
| --- | --- | --- |
| GET | `/health` | 200 with `{"status":"ok"}` when SQLite is available |
| POST | `/books` | 201 with the created book and a `Location` header |
| GET | `/books` | 200 with a JSON array, ordered by ID |
| GET | `/books/{id}` | 200 with the book |
| PUT | `/books/{id}` | 200 with the replacement book |
| DELETE | `/books/{id}` | 204 with an empty body |

POST and PUT accept JSON with non-blank string fields `title` and `author`. The optional fields `year` (32-bit signed integer) and `isbn` (string) default to null. PUT replaces all four fields. The service assigns an integer `id` on creation. The optional `author` query parameter uses an exact, case-sensitive match.

Errors return a JSON object with an `error` message. Malformed JSON or invalid path parameters return 400, a missing or unsupported JSON content type returns 415, invalid book fields return 422, and an unknown book ID returns 404. The health endpoint returns 503 if SQLite is unavailable.

```sh
curl -i http://127.0.0.1:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia Butler","year":1979,"isbn":"9780807083697"}'

curl 'http://127.0.0.1:3000/books?author=Octavia%20Butler'
```
