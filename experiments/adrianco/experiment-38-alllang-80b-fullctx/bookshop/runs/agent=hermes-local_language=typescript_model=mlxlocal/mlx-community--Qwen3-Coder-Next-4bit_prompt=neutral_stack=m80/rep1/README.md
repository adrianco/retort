# Book API REST Service

A REST API service for managing a book collection built with Express.js, TypeScript, and SQLite.

## Features

- **CRUD Operations**: Create, Read, Update, Delete books
- **Filtering**: Filter books by author
- **Input Validation**: Validates all required fields
- **Health Check**: Endpoint to check service status
- **SQLite Storage**: Embedded database for persistent storage

## API Endpoints

### Health Check
- `GET /health` - Returns service status

### Books
- `POST /books` - Create a new book
- `GET /books` - List all books (supports `?author=` filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book

## Prerequisites

- Node.js (v16 or higher)
- npm or yarn

## Installation

```bash
npm install
```

## Development

Run in development mode:

```bash
npm run dev
```

## Building

Build the TypeScript code:

```bash
npm run build
```

## Running

Run the built server:

```bash
npm start
```

The server will start on port 3000 (or the PORT environment variable).

## Testing

Run all tests:

```bash
npm test
```

Run tests in watch mode:

```bash
npm run test:watch
```

## Example Usage

### Create a Book

```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0743273565"
  }'
```

### List All Books

```bash
curl http://localhost:3000/books
```

### Filter by Author

```bash
curl "http://localhost:3000/books?author=F.%20Scott%20Fitzgerald"
```

### Get a Book by ID

```bash
curl http://localhost:3000/books/{book-id}
```

### Update a Book

```bash
curl -X PUT http://localhost:3000/books/{book-id} \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby (Updated)",
    "year": 1926
  }'
```

### Delete a Book

```bash
curl -X DELETE http://localhost:3000/books/{book-id}
```

### Health Check

```bash
curl http://localhost:3000/health
```

## Project Structure

```
src/
├── controllers/
│   ├── BookController.ts
│   ├── HealthController.ts
│   └── index.ts
├── middleware/
│   ├── validation.ts
│   └── index.ts
├── services/
│   ├── BookService.ts
│   └── index.ts
├── database/
│   ├── database.ts
│   └── index.ts
├── server.ts
└── index.ts
tests/
├── unit.test.ts
├── integration.test.ts
└── validation.test.ts
```

## License

ISC
