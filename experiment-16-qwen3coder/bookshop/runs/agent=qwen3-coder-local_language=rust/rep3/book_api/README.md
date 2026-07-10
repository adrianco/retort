# Book API

A REST API service for managing a book collection.

## Features

- Create books with title, author, year, and ISBN
- List all books with optional author filter
- Get a single book by ID
- Update books
- Delete books
- Health check endpoint

## Requirements

- Rust 1.60 or later
- Cargo

## Setup

1. Clone the repository
2. Navigate to the project directory
3. Build the project:
   ```bash
   cargo build
   ```

## Running

To start the server:
```bash
cargo run
```

The server will start on `http://127.0.0.1:3000`.

## API Endpoints

### Health Check
- **GET** `/health` - Check if the service is running

### Books
- **POST** `/books` - Create a new book
- **GET** `/books` - List all books (supports `?author=` filter)
- **GET** `/books/{id}` - Get a single book by ID
- **PUT** `/books/{id}` - Update a book
- **DELETE** `/books/{id}` - Delete a book

## Usage Examples

### Create a book
```bash
curl -X POST http://127.0.0.1:3000/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Rust Programming Language",
    "author": "Steve Klabnik and Carol Nichols",
    "year": 2018,
    "isbn": "978-0998745505"
  }'
```

### List all books
```bash
curl http://127.0.0.1:3000/books
```

### Get a book by ID
```bash
curl http://127.0.0.1:3000/books/1
```

### Update a book
```bash
curl -X PUT http://127.0.0.1:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Rust Programming Language - Updated Edition",
    "author": "Steve Klabnik and Carol Nichols",
    "year": 2018,
    "isbn": "978-0998745505"
  }'
```

### Delete a book
```bash
curl -X DELETE http://127.0.0.1:3000/books/1
```

## Testing

Run the tests with:
```bash
cargo test
```

## Database

The application uses SQLite as an embedded database. The database file `books.db` will be created in the project directory.