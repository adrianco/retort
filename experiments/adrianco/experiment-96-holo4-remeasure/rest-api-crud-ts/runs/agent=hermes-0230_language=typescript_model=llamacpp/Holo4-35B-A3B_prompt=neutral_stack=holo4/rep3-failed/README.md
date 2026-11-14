# Book Collection REST API

A REST API service for managing a book collection, built with Express and SQLite.

## Endpoints

- **POST** `/books` — Create a new book (body: `title`, `author`, optional `year`, `isbn`)
- **GET** `/books` — List all books (supports `?author=` query filter)
- **GET** `/books/:id` — Get a single book by ID
- **PUT** `/books/:id` — Update a book
- **DELETE** `/books/:id` — Delete a book
- **GET** `/health` — Health check

## Setup

```bash
npm install
```

## Running

```bash
# Development (with ts-node)
npm run dev

# Production (compiled)
npm run build
npm start
```

## Testing

```bash
npm test
```
