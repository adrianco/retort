# Book API REST Service

A REST API service for managing a book collection, built with Node.js, Express, and SQLite.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST   | `/books` | Create a new book |
| GET    | `/books` | List all books (supports `?author=` filter) |
| GET    | `/books/:id` | Get a single book by ID |
| PUT    | `/books/:id` | Update a book |
| DELETE | `/books/:id` | Delete a book |
| GET    | `/health` | Health check |

## Setup

```bash
npm install
```

## Run

```bash
npm run build
npm start
```

Or for development with auto-reload:

```bash
npm run dev
```

## Test

```bash
npm test
```
