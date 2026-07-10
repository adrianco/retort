# Book Collection API

A REST API service for managing a book collection with SQLite database.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- Input validation

## Endpoints

- `POST /books` - Create a new book
- `GET /books` - List all books (supports ?author= filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Build the project:
   ```bash
   npm run build
   ```

3. Start the server:
   ```bash
   npm start
   ```

4. Run tests:
   ```bash
   npm test
   ```
