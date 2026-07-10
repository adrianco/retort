# Book API Service

A REST API service for managing a book collection implemented in Rust with Actix Web and SQLite.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (support ?author= filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Requirements

- Rust 1.70+
- Cargo

## Setup and Running

1. Clone the repository
2. Navigate to the project directory
3. Run the application:

```bash
cargo run
```

The server will start on `http://127.0.0.1:8080`

## API Endpoints

### Health Check
```
GET /health
```

### Create Book
```
POST /books
Content-Type: application/json

{
  "title": "Book Title",
  "author": "Author Name",
  "year": 2023,
  "isbn": "1234567890"
}
```

### List Books
```
GET /books
GET /books?author=Author+Name
```

### Get Book by ID
```
GET /books/1
```

### Update Book
```
PUT /books/1
Content-Type: application/json

{
  "title": "Updated Title",
  "author": "Updated Author",
  "year": 2024,
  "isbn": "0987654321"
}
```

### Delete Book
```
DELETE /books/1
```

## Database

The application uses SQLite as an embedded database. All data is stored in a file named `books.db` in the project root directory.

## Testing

The application includes unit and integration tests. Run tests with:

```bash
cargo test
```

## Validation

All endpoints include input validation:
- Title and author are required for creating/updating books
- Returns appropriate HTTP status codes (200, 201, 400, 404, 500)

## Dependencies

- Actix Web
- Serde
- SQLx
- Tokio

## License

This project is licensed under the MIT License.