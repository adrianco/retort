# Books API

A REST API for managing a book collection, written in TypeScript with Express 5 and
SQLite (Node's built-in `node:sqlite` module — no native add-on to compile).

## Requirements

- Node.js 22.13+ (24+ recommended)

## Setup and run

```bash
npm install
npm run build
npm start          # listens on http://localhost:3000
```

Environment variables:

| Variable  | Default    | Description                                   |
|-----------|------------|-----------------------------------------------|
| `PORT`    | `3000`     | HTTP port                                     |
| `DB_PATH` | `books.db` | SQLite file (`:memory:` for a transient store) |

## Tests

```bash
npm test
```

Integration tests start the app on a random port against an in-memory database.

## Endpoints

| Method | Path          | Description                          | Success | Errors   |
|--------|---------------|--------------------------------------|---------|----------|
| GET    | `/health`     | Health check                         | 200     |          |
| POST   | `/books`      | Create a book                        | 201     | 400      |
| GET    | `/books`      | List books; `?author=` filters (exact, case-insensitive) | 200 | |
| GET    | `/books/{id}` | Get one book                         | 200     | 404      |
| PUT    | `/books/{id}` | Replace a book (full update)         | 200     | 400, 404 |
| DELETE | `/books/{id}` | Delete a book                        | 204     | 404      |

Book fields: `title` (string, required), `author` (string, required),
`year` (integer, optional), `isbn` (string, optional).

Errors are JSON: `{ "error": "...", "details": ["..."] }`.

## Example

```bash
curl -X POST localhost:3000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'localhost:3000/books?author=Frank%20Herbert'
```
