# Book API

A simple REST API for managing a book collection.

## Technology
- **Node.js** (v18+)
- **TypeScript**
- **Express** for the HTTP server
- **better-sqlite3** for a lightweight SQLite database
- **Jest** + **Supertest** for integration tests

## Setup
```bash
# Install dependencies
npm install
```

## Development
```bash
# Run the server in development mode with ts-node
npm run dev
```
The server listens on port 3000 by default.

## Build & Run
```bash
# Build TypeScript
npm run build
# Start the compiled server
npm start
```

## API Endpoints
- `POST /books` – create a book. Requires `title` and `author`.
- `GET /books` – list all books, optionally filter by `?author=`.
- `GET /books/:id` – get a book by ID.
- `PUT /books/:id` – update a book.
- `DELETE /books/:id` – delete a book.
- `GET /health` – health‑check endpoint.

## Tests
```bash
npm test
```
All integration tests are located in `tests/api.test.ts`.

---

© 2026
