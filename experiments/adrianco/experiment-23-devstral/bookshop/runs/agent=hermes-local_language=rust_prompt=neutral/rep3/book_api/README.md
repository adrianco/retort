# Book API

A REST API for managing a book collection.

## Setup

1. Install Rust and Cargo
2. Clone the repository
3. Run `cargo build` to build the project

## Run

1. Set up the database:
   ```bash
   diesel setup
   ```

2. Run the application:
   ```bash
   cargo run
   ```

## API Endpoints

- POST /books — Create a new book (title, author, year, isbn)
- GET /books — List all books (support ?author= filter)
- GET /books/{id} — Get a single book by ID
- PUT /books/{id} — Update a book
- DELETE /books/{id} — Delete a book
- GET /health — Health check endpoint

## Testing

Run the tests with:
```bash
cargo test
```
