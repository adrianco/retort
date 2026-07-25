# Book API Service

REST API service for managing a book collection built with TypeScript, Express, and SQLite.

## Features

- Create, read, update, and delete books (CRUD operations)
- Filter books by author
- Health check endpoint
- SQLite database for persistent storage
- Input validation

## Setup

1. Install dependencies:

```bash
npm install
```

2. Build the project:

```bash
npm run build
```

## Running

### Development mode

```bash
npm run dev
```

### Production mode

```bash
npm run build
npm start
```

The server will start on port 3000.

## API Endpoints

### Health Check
- `GET /health` - Returns server health status

### Books
- `POST /books` - Create a new book
  - Request body: `{ "title": "string", "author": "string", "year": "number", "isbn": "string" }`
  - Required fields: `title`, `author`
  
- `GET /books` - List all books (supports `?author=` filter)
  
- `GET /books/:id` - Get a single book by ID
  
- `PUT /books/:id` - Update a book
  - Request body: `{ "title": "string", "author": "string", "year": "number", "isbn": "string" }`
  - All fields are optional for update
  
- `DELETE /books/:id` - Delete a book by ID

## Testing

Run tests:

```bash
npm test
```

Run tests with coverage:

```bash
npm test -- --coverage
```

## Project Structure

```
src/
├── database/
│   └── database.ts          # SQLite database connection and initialization
├── models/
│   └── book.model.ts        # Book entity and data access layer
├── routes/
│   └── book.routes.ts       # API routes
├── middleware/
│   └── validation.ts        # Input validation middleware
├── types/
│   └── index.ts             # TypeScript type definitions
├── server.ts                # Express application entry point
tests/
├── integration/
│   └── api.test.ts          # Integration tests for API endpoints
├── unit/
│   └── validation.test.ts   # Unit tests for validation
└── database.test.ts         # Database tests
```
