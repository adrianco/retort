# Interfaces

## HTTP routes

| Method | Path | Description | Status codes |
|--------|------|-------------|--------------|
| GET | /health | DB-ping health check | 200 ok / 503 unhealthy |
| POST | /books | Create a book (title, author, year, isbn) | 201 / 400 / 500 |
| GET | /books | List books, optional `?author=` filter | 200 / 500 |
| GET | /books/{id} | Fetch one book by id | 200 / 400 / 404 / 500 |
| PUT | /books/{id} | Update a book | 200 / 400 / 404 / 500 |
| DELETE | /books/{id} | Delete a book | 204 / 400 / 404 / 500 |

## Data schema

`books` table (SQLite):

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | PK, AUTOINCREMENT |
| title | TEXT | NOT NULL |
| author | TEXT | NOT NULL |
| year | INTEGER | NOT NULL DEFAULT 0 |
| isbn | TEXT | NOT NULL DEFAULT '' |

## Validation

`decode()` trims and rejects empty `title`/`author` with 400, rejects negative
`year` with 400, and rejects malformed JSON with 400.

## Configuration (env)

- `DB_PATH` — SQLite DSN/file (default `books.db`)
- `ADDR` — listen address (default `:8080`)
