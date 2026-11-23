# Book Collection API

This TypeScript service uses Node.js HTTP and SQLite. It requires Node.js 24 or newer and npm.

## Setup and run

```sh
npm ci
npm run build
npm start
```

The service listens on port 3000 and creates `books.sqlite` in the working directory. Set `PORT` or `DATABASE_PATH` to override those defaults.

Run the integration tests with `npm test`.

## API

| Method | Path | Successful response |
| --- | --- | --- |
| GET | `/health` | `200` with `{"status":"ok"}` |
| POST | `/books` | `201` with the created book and a `Location` header |
| GET | `/books` | `200` with an array ordered by ID |
| GET | `/books/{id}` | `200` with the book |
| PUT | `/books/{id}` | `200` with the updated book |
| DELETE | `/books/{id}` | `204` with an empty body |

Use `GET /books?author=Frank%20Herbert` for an exact, case-sensitive author match. Book objects include a generated integer `id` and the fields `title`, `author`, `year`, and `isbn`.

POST and PUT accept JSON objects with non-empty string values for `title` and `author`. The optional `year` must be a safe integer or null. The optional `isbn` must be a non-empty string or null. String values are trimmed. PUT replaces all four fields, and omitted optional fields are stored as null.

Invalid input returns `400` with a JSON error. Missing books return `404`. Request bodies over 64 KiB return `413`.

```sh
curl -i http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
```
