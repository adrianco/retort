# Books API (Rust)

REST API for a book collection using Axum and SQLite (rusqlite, bundled).

## Run
```
cargo run            # listens on 0.0.0.0:3000, stores data in ./books.db
DATABASE_PATH=/tmp/b.db BIND_ADDR=127.0.0.1:8080 cargo run
```

## Test
```
cargo test
```

## Endpoints
| Method | Path | Notes |
|---|---|---|
| GET | /health | `{"status":"ok"}` |
| POST | /books | body: `title`, `author` (required), `year`, `isbn` → 201 |
| GET | /books | optional `?author=` exact-match filter |
| GET | /books/{id} | 404 if missing |
| PUT | /books/{id} | full replace; same validation as POST |
| DELETE | /books/{id} | 204 on success |

Validation errors return 400 with `{"error": ..., "details": [...]}`.
