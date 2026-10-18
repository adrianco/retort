# Book API

A JSON REST API for managing a book collection, built with Rust, Axum, and SQLite.

## Run

Install Rust, then from this directory run:

```sh
cargo run
```

The service listens on `127.0.0.1:3000` and creates `books.db` in the current directory. Set `DATABASE_URL` to change the SQLite database URL and `BIND_ADDR` to change the listen address.

## Endpoints

- `GET /health` — health status
- `POST /books` — create a book (`title`, `author` required; `year` and `isbn` optional)
- `GET /books` — list books; add `?author=Name` to filter by author
- `GET /books/{id}` — fetch a book
- `PUT /books/{id}` — replace a book's fields
- `DELETE /books/{id}` — delete a book

Responses are JSON except successful deletes, which return `204 No Content`. Missing books return `404`; invalid required fields return `400`.

## Tests

Run the integration-style handler tests with:

```sh
cargo test
```
