# Book collection API

On macOS, install Xcode Command Line Tools with `xcode-select --install` if needed. On Linux, install Swift 5.7 or newer and the SQLite development headers (on Debian or Ubuntu, run `sudo apt install libsqlite3-dev pkg-config make`). The service uses Foundation, POSIX sockets and the system SQLite library. Swift Package Manager builds it without downloading package dependencies.

Run `make build` to compile, `make test` to run the tests, or `make run` to start the service. It listens at `http://127.0.0.1:8080` and persists books in `books.sqlite3` in the working directory. Override either setting with environment variables, for example `PORT=9000 BOOKS_DB=/tmp/library.sqlite3 make run`.

| Method | Path | Successful response |
| --- | --- | --- |
| GET | /health | 200 with service status |
| POST | /books | 201 with created book and numeric ID |
| GET | /books | 200 with an array in ID order |
| GET | /books?author=Ursula%20Le%20Guin | 200 with exact, case-sensitive author matches |
| GET | /books/{id} | 200 with book |
| PUT | /books/{id} | 200 with replacement book |
| DELETE | /books/{id} | 200 with deleted ID |

POST and PUT accept a JSON object with nonblank strings for title and author. Year is an optional integer and ISBN is an optional string. PUT replaces all fields and preserves the ID. Invalid input returns 400 and a missing book returns 404. Errors include a JSON `error` message.

```sh
curl -i http://127.0.0.1:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"The Dispossessed","author":"Ursula Le Guin","year":1974,"isbn":"9780061054884"}'
```

The local HTTP/1.1 server handles one request per connection and accepts bodies up to 1 MiB with Content-Length framing.
