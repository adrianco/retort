# Book collection API

Install a JDK (17 or newer) and the Clojure CLI. From this directory, run:

```sh
clojure -M:test
clojure -M:run
```

The CLI downloads dependencies on the first run. The Ring service listens on port 8080 and creates a SQLite database at `books.sqlite`. Set `PORT` and `BOOKS_DB` to choose a different port and database path.

| Request | Result |
| --- | --- |
| GET /health | 200 with service status |
| POST /books | 201 with the created book and its URL in the Location header |
| GET /books | 200 with all books in ID order |
| GET /books?author=Octavia%20Butler | 200 with books matching the exact author name |
| GET /books/{id} | 200 with the requested book |
| PUT /books/{id} | 200 with the replacement book |
| DELETE /books/{id} | 200 with the deleted ID |

Create and replace requests accept a JSON object. Both require nonblank string fields `title` and `author`. The optional fields are `year` (integer) and `isbn` (string, preserving leading zeros). Omitting an optional field on replacement clears it. Invalid bodies return 400 and missing books return 404.

```sh
curl -i http://localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia Butler","year":1979}'
```
