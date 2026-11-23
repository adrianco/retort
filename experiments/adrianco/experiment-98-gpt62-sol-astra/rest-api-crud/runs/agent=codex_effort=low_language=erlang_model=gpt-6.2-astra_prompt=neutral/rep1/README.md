# Book collection API

Install Erlang/OTP 27 or later and Make. The service uses OTP's built-in Inets HTTP server, JSON codec, and DETS embedded database.

Run `make build` to compile, `make test` to run the EUnit handler tests against a temporary database, and `make run` to start the server. It listens on 127.0.0.1:8080 and persists writes to books.dets in the current directory. Set `PORT` and `BOOKS_DB` to override these defaults.

Create a book with the following command. The 201 response includes its generated string ID and a Location header.

```sh
curl -i http://127.0.0.1:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"The Dispossessed","author":"Ursula K. Le Guin","year":1974,"isbn":"9780061054884"}'
```

| Method | Path | Result |
| --- | --- | --- |
| GET | /health | Service status |
| POST | /books | Create a book |
| GET | /books | List books, optionally filtered by exact author using a URL-encoded author query parameter |
| GET | /books/{id} | Retrieve a book |
| PUT | /books/{id} | Replace the book fields, preserving its ID |
| DELETE | /books/{id} | Delete the book and return its ID |

POST and PUT require nonblank title and author strings. Optional fields are an integer year and a string isbn. Invalid input returns 400 and a missing book returns 404.
