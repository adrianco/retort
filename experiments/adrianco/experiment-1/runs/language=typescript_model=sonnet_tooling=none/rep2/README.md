# Book Collection API

A REST API for managing a book collection, built with TypeScript, Express, and SQLite (via better-sqlite3).

## Requirements

- Node.js 18+
- npm

## Setup

```bash
npm install
```

## Run

```bash
# Development (ts-node, no build step)
npm run dev

# Production
npm run build
npm start
```

The server listens on port `3000` by default. Override with the `PORT` environment variable.  
The SQLite database file defaults to `books.db`. Override with the `DB_PATH` environment variable.

## API Endpoints

### Health Check

```
GET /health
```

Response: `200 { "status": "ok" }`

---

### Create a Book

```
POST /books
Content-Type: application/json

{
  "title": "Dune",          // required
  "author": "Frank Herbert", // required
  "year": 1965,             // optional
  "isbn": "978-0441013593"  // optional
}
```

Response: `201` with the created book object.

---

### List Books

```
GET /books
GET /books?author=Herbert   # filter by author (partial, case-insensitive)
```

Response: `200` with an array of book objects.

---

### Get a Book

```
GET /books/:id
```

Response: `200` with the book object, or `404` if not found.

---

### Update a Book

```
PUT /books/:id
Content-Type: application/json

{
  "title": "Dune Messiah",
  "year": 1969
}
```

Only the provided fields are updated. Response: `200` with the updated book object, or `404` if not found.

---

### Delete a Book

```
DELETE /books/:id
```

Response: `204 No Content`, or `404` if not found.

## Tests

```bash
npm test
```
