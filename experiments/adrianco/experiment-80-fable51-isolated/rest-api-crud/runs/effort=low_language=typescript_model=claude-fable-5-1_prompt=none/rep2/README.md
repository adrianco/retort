# Books API

A REST API for managing a book collection, written in TypeScript on Node.js's
built-in `node:http` and `node:sqlite` modules (no runtime dependencies).

## Requirements

- Node.js 22.13+ (24+ recommended; uses the built-in SQLite module)

## Setup

```bash
npm install
```

## Run

```bash
npm run build && npm start   # compile to dist/ and run
npm run dev                  # or run the TypeScript sources directly (Node 24+)
```

Environment variables:

| Variable  | Default    | Description               |
|-----------|------------|---------------------------|
| `PORT`    | `3000`     | Port to listen on         |
| `DB_PATH` | `books.db` | SQLite database file path |

## Test

```bash
npm test            # integration tests against an in-memory database (Node 24+)
npm run typecheck   # type-check sources and tests
```

## Endpoints

| Method | Path          | Description                          | Success |
|--------|---------------|--------------------------------------|---------|
| GET    | `/health`     | Health check                         | 200     |
| POST   | `/books`      | Create a book                        | 201     |
| GET    | `/books`      | List books (optional `?author=` exact-match filter) | 200 |
| GET    | `/books/{id}` | Get one book                         | 200     |
| PUT    | `/books/{id}` | Replace a book                       | 200     |
| DELETE | `/books/{id}` | Delete a book                        | 204     |

Book fields: `title` (string, required), `author` (string, required),
`year` (integer, optional), `isbn` (string, optional).

Errors are JSON: `{"error": "...", "details": ["..."]}` with status 400
(validation / malformed JSON), 404 (not found), 405 (method not allowed) or 413
(body too large).

```bash
curl -X POST localhost:3000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'localhost:3000/books?author=Frank%20Herbert'
```
