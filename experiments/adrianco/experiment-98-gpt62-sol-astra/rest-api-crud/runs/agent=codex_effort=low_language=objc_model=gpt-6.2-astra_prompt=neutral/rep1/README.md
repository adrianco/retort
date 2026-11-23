# Book collection API

On macOS, install the Xcode Command Line Tools with `xcode-select --install` if needed. Run `make` and then `./books`. The Objective-C service uses Foundation and the system SQLite library (SQLite 3.35 or newer). It listens on 127.0.0.1, defaults to port 8080, and stores books in `books.sqlite3` in the working directory. Override these settings with `PORT` and `BOOKS_DB`.

| Method | Path | Successful response |
| --- | --- | --- |
| GET | /health | 200 with service status |
| POST | /books | 201 with the created book and its integer ID |
| GET | /books | 200 with books ordered by ID |
| GET | /books?author=Alice | 200 with exact, case-sensitive author matches |
| GET | /books/{id} | 200 with the book |
| PUT | /books/{id} | 200 with the replacement book |
| DELETE | /books/{id} | 200 with the deleted ID |

POST and PUT accept JSON objects with nonblank string fields `title` and `author`. The optional fields `year` (integer) and `isbn` (string) default to null, including during replacement. Invalid input returns 400 and missing books return 404.

```sh
curl -i http://127.0.0.1:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia Butler","year":1979}'
```

Run `make test` with Python 3 installed. The integration tests send HTTP requests through the executable's single-request `--stdio` mode and use a temporary SQLite database per test.
