# Book collection API

Rust REST service using Axum and embedded SQLite. SQLite is bundled; no database server is needed.

## Setup and run

Install a current stable Rust toolchain (including Cargo) and a C compiler for bundled SQLite, then run from this directory:

```sh
cargo build --locked
cargo run --locked
```

The service listens on `127.0.0.1:3000` and creates `books.db` in the working directory. Data survives restarts. Configure the database file and listening address with environment variables:

```sh
DATABASE_PATH=collection.db BIND_ADDR=0.0.0.0:8080 cargo run --locked
```

The parent directory of the database file must exist. Ctrl-C gracefully shuts down the server.

## API

All responses are JSON, including errors (`{"error":"message"}`). Send request bodies with `Content-Type: application/json`.

| Method | Path | Success |
| --- | --- | --- |
| POST | `/books` | 201, created book and `Location` header |
| GET | `/books` | 200, array ordered by ID |
| GET | `/books?author=Frank%20Herbert` | 200, exact case-sensitive author matches |
| GET | `/books/{id}` | 200, book |
| PUT | `/books/{id}` | 200, replaced book |
| DELETE | `/books/{id}` | 200, `{"deleted":1}` |
| GET | `/health` | 200, `{"status":"ok"}` |

Book IDs are generated positive integers. Create and update require nonblank string `title` and `author`; surrounding whitespace is trimmed. `year` is an optional signed 32-bit integer and `isbn` an optional string; omitted or null values are stored as null. ISBN format and uniqueness are not restricted. PUT replaces all fields, so omitted optional fields become null.

Invalid bodies or IDs return 400, missing books/routes 404, unsupported methods 405, unsupported body media types 415, oversized bodies 413, and internal failures 500. Axum limits JSON bodies to 2 MiB. The health endpoint reports service liveness. This service has no authentication; bind to a trusted interface.

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
curl http://127.0.0.1:3000/health
```

## Verification

```sh
cargo test --locked
cargo fmt --check
cargo clippy --locked --all-targets -- -D warnings
```

Integration tests exercise the HTTP router with isolated databases: CRUD, filtering, validation without mutation, error responses, health, and persistence after reopening a file database. Blocking SQLite operations run on Tokio's blocking thread pool and a mutex serializes access to the connection.
