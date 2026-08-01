# Book Collection API

A TypeScript REST API using Node's built-in HTTP server and SQLite (`node:sqlite`). It requires Node.js 22.5 or later; Node 22.6+ is recommended for direct TypeScript execution.

## Run

```sh
npm start
```

The service listens on port `3000` by default. Set `PORT` to change it and `DATABASE_PATH` to choose the SQLite database file (default: `books.db`).

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Health check |
| POST | `/books` | Create a book |
| GET | `/books?author=Name` | List books, optionally filtered by author |
| GET | `/books/:id` | Get one book |
| PUT | `/books/:id` | Update one or more fields |
| DELETE | `/books/:id` | Delete a book |

`title` and `author` are required when creating a book, and cannot be blank when updating. `year` must be an integer if supplied; `isbn` must be a string or `null`.

Example:

```sh
curl -X POST http://localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Kindred","author":"Octavia Butler","year":1979}'
```

## Test and build check

```sh
npm test
npm run build
```
