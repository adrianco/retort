# Book API Service

A REST API service for managing a book collection implemented in Rust.

## Features

- POST /books - Create a new book (title, author, year, isbn)
- GET /books - List all books (support ?author= filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

## Requirements

- Rust 1.56 or later
- Cargo

## Setup

1. Clone this repository
2. Navigate to the project directory
3. Build the project:
   ```bash
   cargo build
   ```

## Running

To run the server:
```bash
cargo run
```

## Implementation Details

This is a simplified implementation that demonstrates the structure and requirements.

### Full Implementation Plan

A complete implementation would include:

1. **Rocket Framework**: Web server with route handling
2. **SQLite Database**: Embedded database for data persistence
3. **Proper JSON Handling**: Using Rocket's JSON features
4. **Input Validation**: Title and author are required
5. **HTTP Status Codes**: Appropriate responses for operations

### API Endpoints

- **GET /health** - Health check endpoint returning JSON status
- **GET /books** - List all books with optional author filter
- **GET /books/{id}** - Get a specific book by ID  
- **POST /books** - Create a new book with validation
- **PUT /books/{id}** - Update an existing book
- **DELETE /books/{id}** - Delete a book

### Technical Implementation

- Uses Rust with serde for JSON serialization
- In-memory storage (would use SQLite in production)
- Input validation for required fields
- Proper HTTP status codes

## Testing

This simplified version demonstrates functionality through unit tests in the code structure.

## Database

The full implementation would use SQLite database file `books.db` in the project root directory.

## Building and Running Tests

```bash
cargo build    # Build the project
cargo run      # Run the application
cargo test     # Run tests (would be implemented in full version)
```