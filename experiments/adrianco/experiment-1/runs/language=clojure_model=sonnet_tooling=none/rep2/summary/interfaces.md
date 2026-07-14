# Interfaces

## HTTP Routes

| Method | Path | Returns | Handler | Status Codes |
|--------|------|---------|---------|--------------|
| GET | /health | `{status: "ok"}` | `health-handler` | 200 |
| POST | /books | `{id, title, author, year, isbn}` | `create-book-handler` | 201, 400 |
| GET | /books | `[{id, title, author, year, isbn}]` | `list-books-handler` | 200 |
| GET | /books/:id | `{id, title, author, year, isbn}` | `get-book-handler` | 200, 404 |
| PUT | /books/:id | `{id, title, author, year, isbn}` | `update-book-handler` | 200, 400, 404 |
| DELETE | /books/:id | (empty) | `delete-book-handler` | 204, 404 |

**Query Parameters:**
- GET /books: `?author={substring}` — filters books by partial author match using LIKE

**Request Body (JSON):**
- POST /books: `{title, author, year?, isbn?}` — title and author required
- PUT /books/:id: `{title, author, year?, isbn?}` — title and author required

**Data Schema:**

`books` table:
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `title` TEXT NOT NULL
- `author` TEXT NOT NULL
- `year` INTEGER (nullable)
- `isbn` TEXT (nullable)

## Validation

- title: must be non-empty string
- author: must be non-empty string
- year: optional integer
- isbn: optional string
