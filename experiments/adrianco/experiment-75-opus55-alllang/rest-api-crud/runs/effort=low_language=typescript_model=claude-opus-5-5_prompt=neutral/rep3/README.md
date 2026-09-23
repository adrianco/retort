# Books API

REST API for managing a book collection — TypeScript, Express, and SQLite (Node's built-in `node:sqlite`).

## Requirements
Node.js 22.5+ (built-in `node:sqlite`; developed on Node 26).

## Setup & run
```bash
npm install
npm run build
npm start            # http://localhost:3000
```
Environment variables: `PORT` (default 3000), `DB_PATH` (default `books.db`).

## Tests
```bash
npm test
```

## Endpoints
| Method | Path | Description |
|---|---|---|
| GET | /health | Health check → `{"status":"ok"}` |
| POST | /books | Create (`title`, `author` required; `year` integer, `isbn` string optional) → 201 |
| GET | /books?author= | List all, optionally filtered by exact author |
| GET | /books/:id | Get one → 200 / 404 |
| PUT | /books/:id | Replace a book (same validation as POST) → 200 / 400 / 404 |
| DELETE | /books/:id | Delete → 204 / 404 |

Validation errors return 400 with `{"errors": [...]}`.

```bash
curl -X POST localhost:3000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```
