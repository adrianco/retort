# Book Collection API

A REST API for managing a book collection, built with TypeScript, Express, and SQLite.

## Setup

```bash
npm install
```

## Run

Development (ts-node):
```bash
npm run dev
```

Production (compile first):
```bash
npm run build
npm start
```

The server listens on port 3000 by default. Override with the `PORT` environment variable. The SQLite database file defaults to `books.db`; override with `DB_PATH`.

## Test

```bash
npm test
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| POST | /books | Create a book |
| GET | /books | List all books (optional `?author=` filter) |
| GET | /books/:id | Get a book by ID |
| PUT | /books/:id | Update a book |
| DELETE | /books/:id | Delete a book |

### Book schema

```json
{ "id": 1, "title": "...", "author": "...", "year": 2024, "isbn": "..." }
```

`title` and `author` are required on POST and PUT; `year` and `isbn` are optional.

### Example

```bash
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Clean Code","author":"Robert Martin","year":2008}'

curl http://localhost:3000/books?author=Robert+Martin
```
