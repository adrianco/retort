# Book Collection API

REST API in TypeScript using Node's built-in `http` server and embedded SQLite (`node:sqlite`). No runtime dependencies.

## Requirements
- Node.js 22.13+ (tested on 26)

## Setup & run
```bash
npm install
npm run build
npm start            # PORT=3000, DB_PATH=books.db by default
```

## Test
```bash
npm test
```

## Endpoints
| Method | Path | Description |
|---|---|---|
| GET | /health | Health check |
| POST | /books | Create book (`title`, `author` required; `year` integer, `isbn` string optional) |
| GET | /books?author= | List books, optional case-insensitive author filter |
| GET | /books/{id} | Get book |
| PUT | /books/{id} | Replace book (same validation as POST) |
| DELETE | /books/{id} | Delete book (204) |

Errors return JSON `{ "error": ..., "details"?: [...] }` with 400/404/405/500.

Example:
```bash
curl -X POST localhost:3000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'
```
