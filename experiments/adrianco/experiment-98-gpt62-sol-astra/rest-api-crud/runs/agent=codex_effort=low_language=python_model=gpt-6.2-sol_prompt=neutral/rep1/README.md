# Book Collection API

The service requires Python 3.9 or newer and uses the standard library. It creates its SQLite database on startup.

## Run locally

Run this command from the workspace directory.

```sh
python3 app.py
```

The development server listens at `http://127.0.0.1:8000` and stores data in `books.sqlite3`. Use `--host`, `--port`, or `--database` to override those defaults. To host with a WSGI server, use the callable returned by `app.create_app(database)`.

## Endpoints

| Method and path | Successful response |
| --- | --- |
| `GET /health` | `200` with `{"status":"ok"}` |
| `POST /books` | `201` with the created book and a `Location` header |
| `GET /books` | `200` with an array of books ordered by ID |
| `GET /books/{id}` | `200` with one book |
| `PUT /books/{id}` | `200` with the replacement book |
| `DELETE /books/{id}` | `204` with an empty body |

POST and PUT accept a JSON object. Both require nonblank strings for `title` and `author`. The optional fields `year` (integer) and `isbn` (string) default to `null` when omitted, including on PUT. The server assigns the integer ID. The author filter performs an exact, case-sensitive match.

```sh
curl -i http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia E. Butler","year":1979,"isbn":"9780807083697"}'

curl -G http://127.0.0.1:8000/books --data-urlencode 'author=Octavia E. Butler'
```

Errors have a JSON `error` field. Invalid inputs return `400`, bodies larger than 64 KiB return `413`, and missing books return `404`.

## Run tests

```sh
python3 -m unittest -v
```
