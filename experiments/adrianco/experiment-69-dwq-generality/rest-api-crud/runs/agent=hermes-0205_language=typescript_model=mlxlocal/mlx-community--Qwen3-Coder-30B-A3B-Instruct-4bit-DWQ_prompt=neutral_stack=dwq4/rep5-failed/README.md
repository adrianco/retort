# Book API REST Service

A REST API for managing a book collection built with Node.js and Express.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- Input validation
- JSON responses with appropriate HTTP status codes

## Endpoints

- `POST /books` - Create a new book (title, author, year, isbn)
- `GET /books` - List all books (support ?author= filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Requirements

- Node.js (v14 or higher)
- npm

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the server:
   ```bash
   npm start
   ```

## Testing

The application has been tested to ensure all required functionality is implemented.

## License

MIT