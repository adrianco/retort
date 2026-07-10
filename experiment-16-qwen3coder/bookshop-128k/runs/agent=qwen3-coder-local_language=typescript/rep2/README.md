# Book Collection REST API

A REST API service for managing a book collection with SQLite database storage.

## Features

- POST /books — Create a new book (title, author, year, isbn)
- GET /books — List all books (support ?author= filter)
- GET /books/{id} — Get a single book by ID
- PUT /books/{id} — Update a book
- DELETE /books/{id} — Delete a book
- GET /health — Health check endpoint

## Requirements

- Node.js (v14 or higher)
- npm

## Setup

1. Install dependencies:
   ```
   npm install
   ```

2. Start the server:
   ```
   npm start
   ```

3. Run tests:
   ```
   npm test
   ```

## API Endpoints

### Health Check
- `GET /health` - Returns server health status

### Books Management
- `POST /books` - Create a new book
- `GET /books` - List all books (supports ?author= filter)
- `GET /books/:id` - Get a single book by ID
- `PUT /books/:id` - Update a book
- `DELETE /books/:id` - Delete a book

## Database

The application uses SQLite for data persistence. The database file is created automatically in the project root.

## Testing

Tests are written using Mocha and Chai. Run with:
```
npm test
```