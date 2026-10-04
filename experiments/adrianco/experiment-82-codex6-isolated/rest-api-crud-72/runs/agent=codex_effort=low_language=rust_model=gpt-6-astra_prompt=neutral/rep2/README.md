# Book collection API

Rust REST service using Axum and embedded SQLite. Requires a Rust toolchain
with Cargo and a C compiler for bundled SQLite; no separate database server is needed.

```sh
cargo build --locked
cargo run --locked
```

The service listens on `127.0.0.1:3000` and creates `books.db` in the current
directory. Data persists across restarts. Override settings with environment variables:

```sh
DATABASE_PATH=/tmp/my-books.db BIND_ADDRESS=0.0.0.0:8080 cargo run --locked
```

Use Ctrl-C for graceful shutdown. SQLite work runs on blocking worker threads.

| Method | Path | Success |
| --- | --- | --- |
| POST | `/books` | 201, created book and Location header |
| GET | `/books` | 200, array ordered by ID |
| GET | `/books?author=Frank%20Herbert` | 200, exact case-sensitive author matches |
| GET | `/books/{id}` | 200, book |
| PUT | `/books/{id}` | 200, replaced book |
| DELETE | `/books/{id}` | 204, empty body |
| GET | `/health` | 200, `{"status":"ok"}` after a database check |

POST and PUT accept JSON with required string fields `title` and `author`.
They are trimmed and must not be blank. `year` is an optional signed 32-bit
integer and `isbn` an optional string; either may be null. No ISBN format or
uniqueness restriction is imposed. Unknown fields are rejected. PUT replaces
all fields: omitted year/isbn become null. IDs are server-generated positive integers.

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

Errors use `{"error":"message"}`: invalid input returns 400, missing JSON
content type 415, missing books/routes 404, unsupported methods 405, and internal
errors 500. The default JSON request body limit is 2 MiB (413 if exceeded).
The service has no authentication and is intended for local use or deployment
behind an appropriately configured gateway.

Run the tests and checks:

```sh
cargo test --locked
cargo fmt --check
cargo clippy --locked --all-targets -- -D warnings
```

Tests cover CRUD, author filtering, required-field validation, malformed requests,
missing IDs, health, and persistence after reopening SQLite.
