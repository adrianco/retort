# Book API

A REST API service for managing a book collection using Rust and Actix Web.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- SQLite database for storage
- Input validation

## Setup and Run

### Prerequisites

- Rust and Cargo installed
- SQLite

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/book_api.git
   cd book_api
   ```

2. Install dependencies:
   ```bash
   cargo build
   ```

### Running the API

```bash
cargo run
```

The API will be available at `http://127.0.0.1:8080`.

## API Endpoints

- `GET /health`: Health check
- `POST /books`: Create a new book
- `GET /books`: List all books (with optional `?author=` filter)
- `GET /books/{id}`: Get a single book by ID
- `PUT /books/{id}`: Update a book
- `DELETE /books/{id}`: Delete a book

## Example Request

```bash
curl -X POST -H "Content-Type: application/json" -d '{"title": "The Rust Programming Language", "author": "Steve Klabnik", "year": 2018, "isbn": "978-1593278281"}' http://127.0.0.1:8080/books
```

## Running Tests

```bash
cargo test
```

## License

MIT
