# books-api

A small REST API for managing a book collection. Built with Rust, [axum](https://github.com/tokio-rs/axum), and SQLite (via `sqlx`).

## Requirements

- Rust 1.75+ (any recent stable toolchain)
- No external services needed — SQLite is embedded.

## Run

```bash
cargo run
```

By default the server listens on `0.0.0.0:3000` and stores data in `./books.db`.

Override via environment variables:

- `BIND_ADDR` — e.g. `127.0.0.1:8080`
- `DATABASE_URL` — e.g. `sqlite://path/to/file.db` or `sqlite::memory:`

## Test

```bash
cargo test
```

Integration tests run against an in-memory SQLite database; no setup required.

## Endpoints

| Method | Path             | Description                                        |
| ------ | ---------------- | -------------------------------------------------- |
| GET    | `/health`        | Health check — returns `{"status":"ok"}`.          |
| POST   | `/books`         | Create a book. Body: `{title, author, year?, isbn?}`. |
| GET    | `/books`         | List books. Optional query: `?author=Name`.        |
| GET    | `/books/{id}`    | Fetch a single book by ID.                         |
| PUT    | `/books/{id}`    | Update a book (partial — supply any subset of fields). |
| DELETE | `/books/{id}`    | Delete a book.                                     |

### Validation

`title` and `author` are required when creating a book and cannot be set to empty/whitespace-only strings on update. Validation failures return `400 Bad Request` with `{"error": "..."}`.

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — validation failure
- `404 Not Found` — unknown book ID
- `500 Internal Server Error` — unexpected database error

## Example

```bash
# Create
curl -sX POST localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"The Rust Programming Language","author":"Steve Klabnik","year":2019,"isbn":"978-1718500440"}'

# List by author
curl -s 'localhost:3000/books?author=Steve%20Klabnik'

# Get one
curl -s localhost:3000/books/<id>

# Update
curl -sX PUT localhost:3000/books/<id> \
  -H 'content-type: application/json' \
  -d '{"year":2020}'

# Delete
curl -sX DELETE localhost:3000/books/<id> -i
```

## Project layout

```
src/
├── main.rs       # binary entrypoint — config + server boot
├── lib.rs        # axum Router wiring
├── db.rs         # SQLite pool init + schema bootstrap
├── models.rs     # Book + request/query types
├── handlers.rs   # one handler per endpoint
└── error.rs      # ApiError + IntoResponse mapping
tests/
└── api.rs        # end-to-end tests using an in-memory DB
```
