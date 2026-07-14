# Book API

REST API for managing a book collection, written in TypeScript with Express and SQLite.

## Setup

```bash
npm install
```

## Run

```bash
npm run build
npm start
```

Or in dev mode:

```bash
npm run dev
```

The server listens on port `3000` by default (override with `PORT`). Data is stored in `books.db` (override with `DB_PATH`).

## Test

```bash
npm test
```

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Health check |
| POST | `/books` | Create a book (body: `title`, `author`, optional `year`, `isbn`) |
| GET | `/books` | List books; optional `?author=` filter |
| GET | `/books/:id` | Get one book |
| PUT | `/books/:id` | Update a book |
| DELETE | `/books/:id` | Delete a book |

### Example

```bash
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```
