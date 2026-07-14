# Book Collection API

A REST API for managing a book collection, built with TypeScript, Express, and SQLite.

## Setup

```bash
npm install
```

## Run

```bash
# Development (with ts-node)
npm run dev

# Production build
npm run build
npm start
```

The server starts on port 3000 by default. Set the `PORT` environment variable to change it.

## API Endpoints

### Health Check
```
GET /health
```
Returns `{ "status": "ok" }`.

### Create a Book
```
POST /books
Content-Type: application/json

{
  "title": "The Pragmatic Programmer",  // required
  "author": "David Thomas",             // required
  "year": 1999,                         // optional
  "isbn": "978-0135957059"              // optional
}
```
Returns `201 Created` with the created book object.

### List Books
```
GET /books
GET /books?author=Thomas
```
Returns `200 OK` with an array of books. Optionally filter by `author` (partial match).

### Get a Book
```
GET /books/:id
```
Returns `200 OK` with the book, or `404 Not Found`.

### Update a Book
```
PUT /books/:id
Content-Type: application/json

{
  "title": "Updated Title",
  "year": 2024
}
```
Returns `200 OK` with the updated book, or `404 Not Found`. Only provided fields are updated.

### Delete a Book
```
DELETE /books/:id
```
Returns `204 No Content`, or `404 Not Found`.

## Tests

```bash
npm test
```
