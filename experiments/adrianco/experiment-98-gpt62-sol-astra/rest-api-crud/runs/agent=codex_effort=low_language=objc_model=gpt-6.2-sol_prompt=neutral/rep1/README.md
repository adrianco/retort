# Book Collection API

This Objective-C service uses macOS Foundation for JSON and SQLite for storage. Build it with the macOS SDK and Clang from Xcode or the Xcode Command Line Tools. The runtime SQLite version must be 3.35 or newer.

```sh
make
make test
./book-service 8080 books.sqlite3
```

The service listens on `127.0.0.1`. Both arguments are optional and default to the values above. Pass port `0` to have the OS choose an available port. The service prints its address at startup and creates the database file if needed.

| Method and path | Successful response |
| --- | --- |
| `GET /health` | `200` with `{"status":"ok"}` |
| `POST /books` | `201` with the new book and a `Location` header |
| `GET /books` | `200` with an array of books in ID order |
| `GET /books?author=Frank%20Herbert` | `200` with books whose author matches the decoded value exactly |
| `GET /books/{id}` | `200` with the requested book |
| `PUT /books/{id}` | `200` with the replacement book and its existing ID |
| `DELETE /books/{id}` | `204` with an empty body |

POST and PUT accept a JSON object. Supply nonblank strings for `title` and `author`. Optional fields are `year` (a JSON integer in the range ±9,007,199,254,740,991) and `isbn` (a string). Omitted optional fields are stored as `null`, including on PUT. The server assigns the integer `id`.

Invalid inputs return `400`. Missing books or routes return `404`. Unsupported methods on known routes return `405`. Errors have a JSON `error` field. The local server handles one request per connection. Send request bodies with `Content-Length` and keep them at or below 1 MiB.

```sh
curl -i http://127.0.0.1:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl 'http://127.0.0.1:8080/books?author=Frank%20Herbert'
```

The test suite exercises the request handler with SQLite and covers the CRUD lifecycle, validation, health, author filtering, and persistence after reopening a database.
