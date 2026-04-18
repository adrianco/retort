# Interfaces

## HTTP API

### Endpoints

| Method | Path | Handler | Status Codes | Description |
|--------|------|---------|--------------|-------------|
| GET | /health | `handlers/health-handler` | 200 | Health check, returns `{"status":"ok"}` |
| GET | /books | `handlers/list-books-handler` | 200 | List all books, with optional `?author=` filter |
| POST | /books | `handlers/create-book-handler` | 201, 422 | Create new book; returns 422 if title or author missing |
| GET | /books/:id | `handlers/get-book-handler` | 200, 404 | Get single book by ID; returns 404 if not found |
| PUT | /books/:id | `handlers/update-book-handler` | 200, 404, 422 | Update book fields; returns 404 if book missing, 422 if validation fails |
| DELETE | /books/:id | `handlers/delete-book-handler` | 204, 404 | Delete book; returns 404 if book missing |

### Request/Response Format

**Content-Type:** application/json

**Book object schema:**
```json
{
  "id": integer,
  "title": string (required),
  "author": string (required),
  "year": integer | null,
  "isbn": string | null,
  "created_at": string (ISO 8601 timestamp)
}
```

**Error responses:**
```json
{
  "error": string
}
```

**Query parameters:**
- `GET /books?author=<substring>` — filters books by author name (LIKE query)

### Input Validation

- POST /books: title and author required (non-empty)
- PUT /books/:id: title and author optional (if provided, both must be non-empty); updates only provided fields
- GET /books/:id: id must be parseable as integer

## Data Schema

### SQLite tables

**books** table:
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `title` TEXT NOT NULL
- `author` TEXT NOT NULL
- `year` INTEGER (nullable)
- `isbn` TEXT (nullable)
- `created_at` TEXT DEFAULT (datetime('now'))

## Configuration

**Database:** SQLite file at `books.db` (local filesystem)

**Server:** Jetty HTTP adapter
- Default port: 3000 (overridable via `PORT` environment variable)
- Middleware: muuntaja (JSON/format negotiation), reitit routing

**Startup command:** `clojure -M:run` or `java -cp ...` with entry point `book-api.core/-main`
