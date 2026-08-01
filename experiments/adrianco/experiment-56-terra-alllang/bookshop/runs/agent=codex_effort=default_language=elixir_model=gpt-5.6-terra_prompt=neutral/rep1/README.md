# Book API

A small REST service written in Elixir. It uses SQLite (`sqlite3`, available on macOS and most Linux distributions) as its embedded database and has no Hex dependencies.

## Run

```sh
mix run --no-halt
```

The API listens on `http://localhost:4000` and creates `books.db` in the project directory. Set `PORT` to use another port, for example `PORT=8080 mix run --no-halt`.

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Service health check |
| POST | `/books` | Create a book |
| GET | `/books?author=Name` | List books, optionally filtered by exact author |
| GET | `/books/:id` | Fetch a book |
| PUT | `/books/:id` | Replace a book |
| DELETE | `/books/:id` | Delete a book |

Book request JSON accepts `title`, `author`, `year`, and `isbn`. `title` and `author` are required. Successful creation returns `201`; deletion returns `204`; invalid book input returns `422`; and missing resources return `404`.

For example:

```sh
curl -X POST http://localhost:4000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Kindred","author":"Octavia Butler","year":1979,"isbn":"9780807083697"}'
curl 'http://localhost:4000/books?author=Octavia%20Butler'
```

## Test

```sh
mix test
```
