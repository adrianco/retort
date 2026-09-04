# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | `/health` | `200 {status:"healthy"}` | `server.js:33` |
| POST | `/books` | `201 Book` \| `400 {error}` \| `500 {error}` | `server.js:38` |
| GET | `/books` | `200 [Book]` (optional `?author=` exact-match filter) \| `500 {error}` | `server.js:71` |
| GET | `/books/:id` | `200 Book` \| `404 {error}` \| `500 {error}` | `server.js:94` |
| PUT | `/books/:id` | `200 Book` \| `400 {error}` \| `404 {error}` \| `500 {error}` | `server.js:116` |
| DELETE | `/books/:id` | `200 {message}` \| `404 {error}` \| `500 {error}` | `server.js:156` |
| * | `*` (unmatched) | `404 {error:"Endpoint not found"}` | `server.js:179` |

## CLI commands

(none — `npm start` runs `node server.js`.)

## Library API

`module.exports = app` (`server.js:201`) — the Express application, imported by `test.js:2`.

## Data schema

`books` table (`server.js:23-29`), file-backed SQLite at `./books.db` (`server.js:12`):
`id` INTEGER PRIMARY KEY AUTOINCREMENT, `title` TEXT NOT NULL, `author` TEXT NOT NULL, `year` INTEGER, `isbn` TEXT.
