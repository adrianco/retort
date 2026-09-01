# Book Collection API

A REST API service for managing a book collection, built with TypeScript, Express, and SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/:id** — Get a single book by ID
- **PUT /books/:id** — Update a book
- **DELETE /books/:id** — Delete a book
- **GET /health** — Health check endpoint

## Prerequisites

- Node.js 18+
- npm (comes with Node.js)

## Setup

1. Install dependencies:

```bash
npm install
```

2. Build the TypeScript project:

```bash
npm run build
```

## Running

Start the server:

```bash
npm start
```

The server runs on port 3000 by default. Set the `PORT` environment variable to change it:

```bash
PORT=8080 npm start
```

For development with auto-reload, use:

```bash
npm run dev
```

## Testing

Run the test suite:

```bash
npm test
```

## API Examples

### Create a book

```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}'
```

### List all books

```bash
curl http://localhost:3000/books
```

### Filter by author

```bash
curl "http://localhost:3000/books?author=F.%20Scott%20Fitzgerald"
```

### Get a book by ID

```bash
curl http://localhost:3000/books/1
```

### Update a book

```bash
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby (Updated)","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}'
```

### Delete a book

```bash
curl -X DELETE http://localhost:3000/books/1
```

### Health check

```bash
curl http://localhost:3000/health
```

## Data Model

| Field  | Type   | Required |
|--------|--------|----------|
| id     | number | Auto     |
| title  | string | Yes      |
| author | string | Yes      |
| year   | number | No       |
| isbn   | string | No       |

## Project Structure

```
├── src/
│   ├── index.ts        # Express server and routes
│   ├── database.ts     # SQLite database setup
│   └── types.ts        # TypeScript type definitions
├── tests/
│   └── api.test.ts     # Integration tests
├── package.json
├── tsconfig.json
├── vitest.config.ts
└── README.md
```
