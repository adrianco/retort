# Interfaces

## HTTP routes

| Method | Path | Behavior | Success | Errors |
|--------|------|----------|---------|--------|
| GET | `/health` | Health check | 200 `{"status":"ok"}` | 405 (non-GET) |
| POST | `/books` | Create a book | 201 + body + `Location` header | 400 (invalid), 405 |
| GET | `/books` | List all books (ID order) | 200 array | 405 |
| GET | `/books?author=X` | Filter by exact author | 200 array | — |
| GET | `/books/{id}` | Get one book | 200 book | 404 |
| PUT | `/books/{id}` | Replace a book | 200 book (same id) | 400, 404, 405 |
| DELETE | `/books/{id}` | Delete a book | 204 empty | 404, 405 |

Unknown paths → 404. All responses are `application/json` except 204.

## Data schema

SQLite table `books`:

```sql
id      INTEGER PRIMARY KEY AUTOINCREMENT
title   TEXT NOT NULL
author  TEXT NOT NULL
year    INTEGER        -- optional, JSON integer, ±(2^53-1)
isbn    TEXT           -- optional
```

## Validation

`title` and `author` must be nonblank strings; `year` (if present) must be a
non-boolean integer in the safe-integer range; `isbn` (if present) must be a
string. Prepared statements parameterize all SQL (injection-safe).
