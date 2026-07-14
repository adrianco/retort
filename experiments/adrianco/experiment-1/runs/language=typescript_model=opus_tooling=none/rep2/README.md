# Book API

A small REST API for managing a book collection. Built with TypeScript, Express, and SQLite (via `better-sqlite3`).

## Setup

```bash
npm install
```

## Run

```bash
# Development (ts runtime)
npm run dev

# Production build + start
npm run build
npm start
```

Environment variables:

- `PORT` (default `3000`)
- `DB_FILE` (default `books.db`; use `:memory:` for an in-memory database)

## Test

```bash
npm test
```

## Endpoints

| Method | Path          | Description                       |
| ------ | ------------- | --------------------------------- |
| GET    | `/health`     | Health check                      |
| POST   | `/books`      | Create a book                     |
| GET    | `/books`      | List books (optional `?author=`)  |
| GET    | `/books/:id`  | Get a single book                 |
| PUT    | `/books/:id`  | Update a book                     |
| DELETE | `/books/:id`  | Delete a book                     |

### Book shape

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441172719"
}
```

`title` and `author` are required on create; `year` and `isbn` are optional.
