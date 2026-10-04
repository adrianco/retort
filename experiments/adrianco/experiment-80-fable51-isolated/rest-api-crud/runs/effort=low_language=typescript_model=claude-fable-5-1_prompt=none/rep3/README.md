# Books API

REST API for managing a book collection, built with TypeScript, Express and SQLite
(Node's built-in `node:sqlite` module, so there are no native dependencies to compile).

## Requirements

- Node.js 24+ (uses the built-in `node:sqlite` module)

## Setup

```bash
npm install
```

## Run

```bash
npm run dev            # run from source
# or
npm run build && npm start
```

Environment variables:

- `PORT` — port to listen on (default `3000`)
- `DB_PATH` — SQLite database file (default `books.db`)

## Test

```bash
npm test
```

Tests run against an in-memory database.

## Endpoints

| Method | Path          | Description                          | Success |
| ------ | ------------- | ------------------------------------ | ------- |
| GET    | `/health`     | Health check                         | 200     |
| POST   | `/books`      | Create a book                        | 201     |
| GET    | `/books`      | List books (optional `?author=`)     | 200     |
| GET    | `/books/{id}` | Get one book                         | 200     |
| PUT    | `/books/{id}` | Replace a book                       | 200     |
| DELETE | `/books/{id}` | Delete a book                        | 204     |

Book fields: `title` (string, required), `author` (string, required), `year` (integer, optional),
`isbn` (string, optional). Invalid input returns `400` with a `details` array; unknown IDs return `404`.

```bash
curl -X POST localhost:3000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
```
