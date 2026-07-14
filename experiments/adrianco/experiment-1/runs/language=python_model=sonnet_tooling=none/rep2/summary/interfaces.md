# Interfaces

## HTTP Routes

| Method | Path | Request | Response | Handler | Status |
|--------|------|---------|----------|---------|--------|
| GET | /health | (none) | `{"status": "ok"}` | `health_check` | 200 |
| POST | /books | `BookCreate` (title, author, year?, isbn?) | `Book` | `create_book` | 201 |
| GET | /books | ?author=filter (optional) | `[Book]` | `list_books` | 200 |
| GET | /books/{id} | (none) | `Book` | `get_book` | 200 or 404 |
| PUT | /books/{id} | `BookUpdate` (partial) | `Book` | `update_book` | 200 or 404 |
| DELETE | /books/{id} | (none) | (no content) | `delete_book` | 204 or 404 |

## Data Schema

**books table:**
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `title` TEXT NOT NULL
- `author` TEXT NOT NULL
- `year` INTEGER (optional)
- `isbn` TEXT (optional)

**Validation:**
- `title` and `author` are required and must not be empty (enforced via Pydantic validators)
- `year` and `isbn` are optional
- LIKE-based filtering on `author` field for list queries
