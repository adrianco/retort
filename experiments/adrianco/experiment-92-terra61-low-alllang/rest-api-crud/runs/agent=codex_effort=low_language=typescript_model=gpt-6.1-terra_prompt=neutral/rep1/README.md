# Book collection API

Requires Node.js 22.13 or later and npm. Node's built-in SQLite module is used for storage.

```sh
npm install
npm run build
npm start
```

The server listens on port 3000 by default. Set `PORT` to change it and `DB_PATH` to choose the SQLite file (default `books.sqlite`). The database and table are created automatically. Run `npm test` to build and execute the integration tests.

All responses are JSON. Book objects have `id`, `title`, `author`, `year`, and `isbn` fields. Title and author must be non-blank strings; year is an optional non-negative integer and ISBN is an optional string. Omitted optional fields are stored as null. PUT replaces the entire book, so title and author are required and omitted optional fields become null.

- `GET /health` returns `{ "status": "ok" }`.
- `POST /books` accepts a JSON book and returns the created book with status 201.
- `GET /books` returns an array. `?author=...` filters by exact, case-sensitive author name.
- `GET /books/{id}` returns a book.
- `PUT /books/{id}` replaces a book and returns it.
- `DELETE /books/{id}` deletes a book and returns a JSON confirmation.

Invalid input returns 400, missing books return 404, and unexpected server errors return 500, with an `error` field in the response. Request bodies are limited to 1 MiB.
