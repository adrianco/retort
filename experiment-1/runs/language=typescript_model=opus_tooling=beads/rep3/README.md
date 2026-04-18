# Books API

REST API for managing a book collection, built with TypeScript, Express, and SQLite (better-sqlite3).

## Setup

```bash
npm install
```

## Run

```bash
npm run build
npm start
```

Dev mode (no build step):

```bash
npm run dev
```

Environment variables:
- `PORT` — HTTP port (default `3000`)
- `DB_PATH` — SQLite file path (default `books.db`)

## Test

```bash
npm test
```

## Endpoints

| Method | Path            | Description                       |
|--------|-----------------|-----------------------------------|
| GET    | `/health`       | Health check                      |
| POST   | `/books`        | Create a book                     |
| GET    | `/books`        | List books (filter `?author=`)    |
| GET    | `/books/:id`    | Get a book by ID                  |
| PUT    | `/books/:id`    | Update a book                     |
| DELETE | `/books/:id`    | Delete a book                     |

Book shape: `{ id, title, author, year, isbn }`. `title` and `author` are required on create.
