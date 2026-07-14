# Book Collection API

A REST API for managing a book collection, built with TypeScript, Express, and SQLite (via `better-sqlite3`).

## Prerequisites

- Node.js 18+
- npm

## Setup

```bash
npm install
```

## Running the Server

### Development (no compilation needed)
```bash
npm run dev
```

### Production
```bash
npm run build
npm start
```

The server listens on port `3000` by default. Override with the `PORT` environment variable:
```bash
PORT=8080 npm start
```

The SQLite database file is created as `books.db` in the working directory. Override with `DB_PATH`:
```bash
DB_PATH=/data/books.db npm start
```

## API

### Health Check
```
GET /health
```
Response: `200 OK` — `{"status":"ok"}`

---

### Create a Book
```
POST /books
Content-Type: application/json

{
  "title": "Clean Code",      // required
  "author": "Robert Martin",  // required
  "year": 2008,               // optional
  "isbn": "9780132350884"     // optional
}
```
Response: `201 Created` — book object with `id`.

---

### List All Books
```
GET /books
GET /books?author=Martin     # filter by author (partial match)
```
Response: `200 OK` — array of book objects.

---

### Get a Book
```
GET /books/:id
```
Response: `200 OK` — book object, or `404 Not Found`.

---

### Update a Book
```
PUT /books/:id
Content-Type: application/json

{ "title": "New Title", "year": 2024 }
```
Response: `200 OK` — updated book object.

---

### Delete a Book
```
DELETE /books/:id
```
Response: `204 No Content`, or `404 Not Found`.

---

## Running Tests

```bash
npm test
```

Tests use an in-memory SQLite database so no file setup is needed.
