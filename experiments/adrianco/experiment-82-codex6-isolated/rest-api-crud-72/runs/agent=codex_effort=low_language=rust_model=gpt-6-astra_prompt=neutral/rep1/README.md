# Book collection API

Rust REST service using Axum and embedded SQLite. SQLite is bundled; no separate database server or SQLite installation is needed.

## Setup and run

Install a current stable Rust toolchain (with Cargo), then run from this directory:

```sh
cargo build
cargo test
cargo run
```

The service listens on `127.0.0.1:3000` and creates `books.db` in the working directory. Data survives restarts. Configure these defaults with environment variables:

```sh
DATABASE_PATH=collection.db BIND_ADDRESS=0.0.0.0:8080 cargo run
```

The database's parent directory must already exist. Press Ctrl-C for graceful shutdown.

## API

All responses, including errors, are JSON. Errors have the form `{"error":"message"}`.

| Method | Path | Result |
| --- | --- | --- |
| GET | `/health` | 200, `{"status":"ok"}` (process liveness) |
| POST | `/books` | 201, created book; `Location` header points to its URL |
| GET | `/books` | 200, array ordered by ID |
| GET | `/books?author=Frank%20Herbert` | 200, exact, case-sensitive author matches |
| GET | `/books/{id}` | 200, book; 404 if absent |
| PUT | `/books/{id}` | 200, replaced book; 404 if absent |
| DELETE | `/books/{id}` | 200, `{"deleted":id}`; 404 if absent |

POST and PUT require a JSON object with nonblank string `title` and `author`. Surrounding whitespace is trimmed. Optional `year` is a signed 32-bit integer or null; optional `isbn` is a string or null. ISBN format and uniqueness are not restricted. Unknown fields, malformed JSON, invalid field types, missing required fields, and noninteger IDs return 400. Unsupported methods return 405. Database failures return 500 without database details.

PUT replaces all editable fields; omitted optional fields become null. IDs are database-generated integers and cannot be supplied in a request body. Unmatched author filters return an empty array.

```sh
curl -i -X POST http://127.0.0.1:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'http://127.0.0.1:3000/books?author=Frank%20Herbert'
curl http://127.0.0.1:3000/books/1
curl -X PUT http://127.0.0.1:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -X DELETE http://127.0.0.1:3000/books/1
```

Tests exercise the HTTP router with isolated SQLite databases: CRUD, filtering, validation, JSON error statuses, health, and persistence after reopening a file database. SQLite access is serialized per process and dispatched to Tokio's blocking pool.
