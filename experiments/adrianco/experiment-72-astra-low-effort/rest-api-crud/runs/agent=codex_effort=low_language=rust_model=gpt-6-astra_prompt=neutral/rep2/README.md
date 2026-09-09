# Book collection API

Rust REST service using Axum and embedded SQLite (bundled, no database server required).

## Setup and run

Install a current stable Rust toolchain and a C compiler for bundled SQLite, then run from this directory:

```sh
cargo build --locked
cargo run --locked
```

The service listens on `127.0.0.1:3000`, creates `books.db` in the current directory, and initializes its schema automatically. Data persists across restarts. Configure with environment variables:

```sh
DATABASE_PATH=/path/to/books.db BIND_ADDR=0.0.0.0:8080 cargo run --locked
```

The database's parent directory must exist. Ctrl-C shuts down gracefully. SQLite work runs on blocking workers, with access serialized through a shared connection and a five-second lock timeout.

## API

| Method | Endpoint | Success |
| --- | --- | --- |
| POST | `/books` | 201, created book and Location header |
| GET | `/books` | 200, array ordered by ID |
| GET | `/books?author=Frank%20Herbert` | 200, exact, case-sensitive author matches |
| GET | `/books/{id}` | 200, book |
| PUT | `/books/{id}` | 200, replaced book |
| DELETE | `/books/{id}` | 204, empty body |
| GET | `/health` | 200, `{"status":"ok"}` after a database query |

POST and PUT require `Content-Type: application/json`. `title` and `author` must be nonblank strings; surrounding whitespace is trimmed. `year` is an optional signed 32-bit integer; `isbn` is an optional string. Both may be null. No ISBN format or uniqueness restriction is imposed. PUT replaces all fields; omitted optional fields become null. IDs are database-generated positive integers.

```sh
curl -i -X POST http://127.0.0.1:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'http://127.0.0.1:3000/books?author=Frank%20Herbert'
curl http://127.0.0.1:3000/books/1
curl -X PUT http://127.0.0.1:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -i -X DELETE http://127.0.0.1:3000/books/1
curl http://127.0.0.1:3000/health
```

Errors return JSON `{"error":"message"}`: 400 for blank fields, malformed JSON, or invalid IDs; 422 for missing required fields or wrong JSON field types; 415 for unsupported content type; 404 for missing books/routes; 405 for unsupported methods; 500 for internal failures. JSON requests have Axum's default 2 MiB limit (413 when exceeded).

## Verify

```sh
cargo test --locked
cargo fmt --check
cargo clippy --locked --all-targets -- -D warnings
```

Seven integration tests exercise CRUD, exact author filtering and SQL metacharacters, validation without mutation, missing books and invalid IDs, JSON errors, health and Location headers, and persistence after reopening SQLite. Each test uses an isolated database.
