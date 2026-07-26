# Interfaces

## HTTP routes

| Method | Path | Description | Success code |
|--------|------|-------------|--------------|
| GET | `/health` | Health check → `{"status":"ok"}` | 200 |
| POST | `/books` | Create a book (title, author required; year, isbn optional) | 201 |
| GET | `/books` | List books; optional `?author=` exact-match filter | 200 |
| GET | `/books/<int:id>` | Get one book (404 if absent) | 200 |
| PUT | `/books/<int:id>` | Partial update; 400 if no fields, 404 if absent | 200 |
| DELETE | `/books/<int:id>` | Delete a book (404 if absent) | 204 |

Error responses are JSON `{"error": "..."}` with 400 (validation) or 404 (missing).

## Data schema

`books` table:

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| title | TEXT | NOT NULL |
| author | TEXT | NOT NULL |
| year | INTEGER | nullable |
| isbn | TEXT | nullable |
