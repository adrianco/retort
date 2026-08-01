# Book Collection API

A Swift REST service backed by SQLite. It uses only the Swift toolchain and the SQLite library included with macOS.

## Run

```sh
swift run book-api
```

The service listens on `http://127.0.0.1:8080`. Pass a port as the first argument, for example `swift run book-api 3000`. Data is persisted to `books.sqlite` in the working directory; set `BOOKS_DB_PATH` to choose another location.

## API

`POST /books` and `PUT /books/{id}` accept JSON such as `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`. `title` and `author` are required.

- `GET /health`
- `POST /books`
- `GET /books` (optionally `?author=Frank%20Herbert`)
- `GET /books/{id}`
- `PUT /books/{id}`
- `DELETE /books/{id}`

Successful creates return `201`, deletes return `204`, missing books return `404`, and invalid input returns `400`. All non-empty responses are JSON.

## Test

```sh
swift test
```
