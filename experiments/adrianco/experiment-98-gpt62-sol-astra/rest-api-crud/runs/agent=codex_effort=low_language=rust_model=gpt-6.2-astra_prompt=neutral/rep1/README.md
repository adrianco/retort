# Book collection API

Install stable Rust and a C compiler for the bundled SQLite library. From this directory, run `cargo run --locked`. The Axum service listens at `http://127.0.0.1:3000` and creates `books.sqlite` in the working directory. Set `BOOKS_ADDR` to change the bind address or `BOOKS_DB` to change the database path.

```sh
curl -i http://127.0.0.1:3000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'http://127.0.0.1:3000/books?author=Frank%20Herbert'
```

| Method and path | Successful response |
| --- | --- |
| POST /books | 201 with the created book and its Location header |
| GET /books | 200 with an array ordered by ID. Optional author filter uses an exact, case-sensitive match. |
| GET /books/{id} | 200 with the book |
| PUT /books/{id} | 200 with the replacement book |
| DELETE /books/{id} | 204 with an empty body |
| GET /health | 200 with `{"status":"ok"}` |

POST and PUT accept JSON objects. Both require nonblank title and author strings and trim surrounding whitespace. The year (32-bit integer) and ISBN (string) are optional. Omitting either on PUT clears its value. The server assigns the numeric ID. Missing books return 404, malformed JSON returns 400, and invalid fields return 422.

Run `cargo test --locked` to execute the route tests against isolated in-memory databases.
