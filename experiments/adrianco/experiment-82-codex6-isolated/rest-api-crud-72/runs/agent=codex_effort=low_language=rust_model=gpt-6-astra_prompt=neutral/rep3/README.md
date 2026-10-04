# Book collection API

Rust REST service using Axum and SQLite. SQLite is bundled with the build; no separate database server is needed.

## Setup and run

Install a current stable Rust toolchain (including Cargo), then run from this directory:

```sh
cargo build --locked
cargo run --locked
```

The service listens at `http://127.0.0.1:3000` and creates `books.db` in the current directory. Data persists across restarts. Configuration is via environment variables:

```sh
DATABASE_PATH=collection.db BIND_ADDRESS=127.0.0.1:8080 cargo run --locked
```

The database's parent directory must already exist. Ctrl-C shuts down gracefully.

## API

| Method | Path | Success |
| --- | --- | --- |
| POST | `/books` | 201, created book and Location header |
| GET | `/books` | 200, array ordered by ID |
| GET | `/books?author=Frank%20Herbert` | 200, exact, case-sensitive author matches |
| GET | `/books/{id}` | 200, book |
| PUT | `/books/{id}` | 200, replaced book |
| DELETE | `/books/{id}` | 204, empty body |
| GET | `/health` | 200, `{"status":"ok"}` after a database query |

POST and PUT accept a JSON object. `title` and `author` must be strings with non-whitespace content; surrounding whitespace is trimmed. `year` is an optional signed 32-bit integer and `isbn` an optional string; both may be null. ISBN format and uniqueness are not constrained. PUT replaces all fields, so omitted optional fields become null. IDs are positive integers assigned by SQLite.

Malformed JSON, invalid field types, missing required fields, blank title/author, and invalid IDs return 400. Missing books/routes return 404; unsupported methods return 405. Internal failures return 500. Errors have the JSON shape `{"error":"message"}`. All nonempty responses are JSON.

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

## Verification

```sh
cargo test --locked
cargo fmt --check
cargo clippy --locked --all-targets -- -D warnings
```

Five integration-style tests exercise the HTTP router with isolated databases: CRUD, filtering (including SQL-injection-like input), validation without mutations, errors and health, and persistence after reopening a file database. SQLite operations run on blocking workers and are serialized through a shared connection.
