# Books API

A small REST API for managing a book collection, built with TypeScript, Express, and SQLite (via `better-sqlite3`).

## Setup

```bash
npm install
```

## Run

Development:

```bash
npm run dev
```

Production (build then start):

```bash
npm run build
npm start
```

Environment variables:

- `PORT` — port to listen on (default `3000`)
- `DB_FILE` — path to SQLite database file (default `books.db`)

## Test

```bash
npm test
```

## Endpoints

| Method | Path           | Description                              |
| ------ | -------------- | ---------------------------------------- |
| GET    | `/health`      | Health check                             |
| POST   | `/books`       | Create a book (`title`, `author` req'd)  |
| GET    | `/books`       | List books, optional `?author=` filter   |
| GET    | `/books/:id`   | Get a book by ID                         |
| PUT    | `/books/:id`   | Update a book (partial updates allowed)  |
| DELETE | `/books/:id`   | Delete a book                            |

Book shape:

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0441013593"
}
```
