# Books API (Rust / Axum / SQLite)

REST service for managing a book collection.

## Setup & run
Requires Rust (stable). SQLite is bundled, no system install needed.

```sh
cargo run                      # listens on 0.0.0.0:3000, stores data in ./books.db
DATABASE_PATH=/tmp/b.db BIND_ADDR=127.0.0.1:8080 cargo run
cargo test                     # run integration tests (in-memory DB)
```

## Endpoints
| Method | Path | Notes |
|---|---|---|
| GET | /health | `{"status":"ok"}` |
| POST | /books | body `{title, author, year?, isbn?}` → 201; 400 if title/author missing |
| GET | /books | optional `?author=` filter (exact, case-insensitive) |
| GET | /books/{id} | 200 or 404 |
| PUT | /books/{id} | full update, same validation → 200 / 400 / 404 |
| DELETE | /books/{id} | 204 or 404 |

Example:
```sh
curl -X POST localhost:3000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```
