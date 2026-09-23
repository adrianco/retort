# Books API (Rust / Axum / SQLite)

REST service for managing a book collection.

## Run
```sh
cargo run --release           # listens on 0.0.0.0:3000, stores data in ./books.db
DATABASE_PATH=/tmp/b.db BIND_ADDR=127.0.0.1:8080 cargo run
```

## Test
```sh
cargo test
```

## Endpoints
| Method | Path | Notes |
|---|---|---|
| GET | /health | `{"status":"ok"}` |
| POST | /books | body `{title, author, year?, isbn?}` → 201; 400 if title/author missing |
| GET | /books | optional `?author=` exact-match filter |
| GET | /books/{id} | 404 if missing |
| PUT | /books/{id} | full replace, same validation → 200 / 400 / 404 |
| DELETE | /books/{id} | 204 / 404 |

Example:
```sh
curl -X POST localhost:3000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```
