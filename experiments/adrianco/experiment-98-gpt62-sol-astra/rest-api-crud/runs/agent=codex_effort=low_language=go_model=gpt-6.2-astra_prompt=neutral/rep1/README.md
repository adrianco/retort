# Book collection API

Install Go 1.22 or newer and a C compiler for the SQLite driver. From this directory, run:

```sh
go test ./...
go build -o books-api .
./books-api
```

The service listens on port 8080 and creates `books.db` in the working directory. Set a different address or database path with `./books-api -addr localhost:9000 -db collection.db`.

Create a book:

```sh
curl -i http://localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
```

| Request | Result |
| --- | --- |
| POST /books | 201 with the book and a Location header |
| GET /books | 200 with an array ordered by ID |
| GET /books?author=Frank%20Herbert | 200 with exact, case-sensitive author matches |
| GET /books/{id} | 200 with the book |
| PUT /books/{id} | 200 with the replacement book |
| DELETE /books/{id} | 204 with an empty body |
| GET /health | 200 when the database is reachable, 503 otherwise |

POST and PUT accept a JSON object with nonblank string fields `title` and `author`. The integer `year` and string `isbn` are optional. Omitting them on replacement clears their previous values. Invalid input returns 400 and missing books return 404. Errors include a JSON `error` field.
