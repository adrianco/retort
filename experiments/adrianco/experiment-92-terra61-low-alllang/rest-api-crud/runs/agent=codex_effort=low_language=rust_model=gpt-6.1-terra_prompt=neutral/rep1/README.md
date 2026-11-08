# Book collection API

A Rust REST API using Axum and SQLite. Install Rust and Cargo, then run:

```sh
cargo run
```

The service listens on `127.0.0.1:3000` and creates `books.db` in the current directory. Set `ADDRESS` (for example, `0.0.0.0:3000`) and `DATABASE_PATH` to change these defaults. SQLite is bundled at build time; a C compiler is required.

```sh
curl -X POST http://127.0.0.1:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'http://127.0.0.1:3000/books?author=Frank%20Herbert'
```

- `POST /books` creates a book and returns it with its ID (201).
- `GET /books` lists books; optional `author` matches the author exactly.
- `GET /books/{id}` returns a book.
- `PUT /books/{id}` replaces all four book fields and returns the updated book.
- `DELETE /books/{id}` deletes a book and returns `{"deleted":true}`.
- `GET /health` returns `{"status":"ok"}`.

Book requests require a nonblank `title` and `author`, an integer `year`, and a string `isbn`. Invalid book bodies return 400; missing books return 404. API errors from these operations contain a JSON `error` field.

Run the integration tests with `cargo test`.
