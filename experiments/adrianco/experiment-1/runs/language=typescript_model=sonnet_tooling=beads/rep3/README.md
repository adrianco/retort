# Book Collection API

A REST API service for managing a book collection, built with TypeScript, Express, and SQLite (via better-sqlite3).

## Setup

```bash
npm install
```

## Running

**Development (with ts-node):**
```bash
npm run dev
```

**Production:**
```bash
npm run build
npm start
```

The server runs on port 3000 by default. Set the `PORT` environment variable to change it.

## API Endpoints

### Health Check
```
GET /health
```
Response: `{ "status": "ok" }`

### Create a Book
```
POST /books
Content-Type: application/json

{
  "title": "Clean Code",      // required
  "author": "Robert Martin",  // required
  "year": 2008,               // optional
  "isbn": "978-0132350884"    // optional
}
```
Returns `201 Created` with the created book object.

### List All Books
```
GET /books
GET /books?author=Martin     # filter by author (partial match)
```
Returns `200 OK` with an array of book objects.

### Get a Book by ID
```
GET /books/:id
```
Returns `200 OK` with the book object, or `404 Not Found`.

### Update a Book
```
PUT /books/:id
Content-Type: application/json

{
  "title": "New Title",   // optional
  "author": "New Author", // optional
  "year": 2024,           // optional
  "isbn": "..."           // optional
}
```
Returns `200 OK` with the updated book, or `404 Not Found`.

### Delete a Book
```
DELETE /books/:id
```
Returns `204 No Content`, or `404 Not Found`.

## Testing

```bash
npm test
```

Runs 15 integration tests covering all endpoints, input validation, and error cases.
