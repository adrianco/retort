# Interfaces

## HTTP routes

| Method | Path | Description | Codes |
|--------|------|-------------|-------|
| GET | /health | Health check → `{status: "ok"}` | 200 |
| GET | /books | List books, optional `?author=` filter | 200 |
| POST | /books | Create book (title, author required; year, isbn optional) | 201 / 400 |
| GET | /books/:id | Fetch one book | 200 / 404 |
| PUT | /books/:id | Full replacement update | 200 / 400 / 404 |
| DELETE | /books/:id | Delete book | 204 / 404 |
| * | (any) | Not-found fallback | 404 |

## Data schema

SQLite table `books`:

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| title | TEXT | NOT NULL |
| author | TEXT | NOT NULL |
| year | INTEGER | nullable |
| isbn | TEXT | nullable |

## Config (env)

- `PORT` — Jetty port (default 3000)
- `DB_PATH` — SQLite file path (default `books.db`)
