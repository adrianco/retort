# Book API Service

A REST API service for managing a book collection with SQLite database storage.

## Features

- Create, read, update, and delete books
- SQLite database persistence
- JSON API responses
- Input validation
- Health check endpoint

## Endpoints

### Health Check
- **GET** `/health` - Check if the service is running

### Books Management
- **POST** `/books` - Create a new book
- **GET** `/books` - List all books
- **GET** `/books/:id` - Get a specific book by ID
- **PUT** `/books/:id` - Update a book by ID
- **DELETE** `/books/:id` - Delete a book by ID

## Requirements

- Rust 1.70+
- Cargo

## Setup

1. Build the project:
   ```bash
   cargo build
   ```

2. Run the server:
   ```bash
   cargo run
   ```

3. The server will start on `http://localhost:3000`

## Usage Examples

### Create a book
```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"9780743273565"}'
```

### List all books
```bash
curl http://localhost:3000/books
```

### Get a specific book
```bash
curl http://localhost:3000/books/<book_id>
```

### Update a book
```bash
curl -X PUT http://localhost:3000/books/<book_id> \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Title","author":"Updated Author"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:3000/books/<book_id>
```

### Health Check
```bash
curl http://localhost:3000/health
```

## Database

The application uses SQLite with a file-based database (`books.db`) in the current directory.

## Testing

Run tests with:
```bash
cargo test
```

## Dependencies

- `axum`: Web framework
- `serde`: JSON serialization
- `sqlx`: SQLite database operations
- `uuid`: Unique identifier generation