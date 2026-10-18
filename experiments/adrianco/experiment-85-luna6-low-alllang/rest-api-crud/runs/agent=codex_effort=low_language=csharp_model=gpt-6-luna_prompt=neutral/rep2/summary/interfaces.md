# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status}` | `Program.cs:11` |
| POST | /books | `201 Book \| 400` | `Program.cs:13` |
| GET | /books | `200 [Book]` (optional `?author=`) | `Program.cs:20` |
| GET | /books/{id} | `200 Book \| 404` | `Program.cs:23` |
| PUT | /books/{id} | `200 Book \| 400 \| 404` | `Program.cs:26` |
| DELETE | /books/{id} | `204 \| 404` | `Program.cs:33` |

## Data schema

`Books` table (SQLite): Id (INTEGER PK AUTOINCREMENT), Title (TEXT NOT NULL), Author (TEXT NOT NULL), Year (INTEGER NULL), Isbn (TEXT NULL). Index `IX_Books_Author` on Author.

## Library API

`BookRepository(connectionString)` — async CRUD over SQLite. `Book(Id, Title, Author, Year?, Isbn?)` and `BookInput(Title?, Author?, Year?, Isbn?)` records.
