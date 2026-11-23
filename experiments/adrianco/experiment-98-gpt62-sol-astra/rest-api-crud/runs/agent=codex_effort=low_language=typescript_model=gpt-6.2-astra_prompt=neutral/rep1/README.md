# Book collection API

Requires Node.js 26 or later and npm. From the project directory, run

```sh
npm ci
npm run build
npm start
```

The service listens on port 3000 and creates `books.sqlite` in the working directory. Set `PORT` and `DB_PATH` to override those defaults. Run `npm test` to compile and run the integration tests using isolated databases.

| Method | Path | Result |
| --- | --- | --- |
| GET | /health | 200 with `{"status":"ok"}` when SQLite responds |
| POST | /books | 201 with the stored book and a Location header |
| GET | /books | 200 with an array ordered by ID. Use `?author=Octavia%20Butler` for a case-sensitive exact match |
| GET | /books/{id} | 200 with one book |
| PUT | /books/{id} | 200 with the replacement book |
| DELETE | /books/{id} | 204 with an empty body |

POST and PUT accept a JSON object. Both require nonblank strings for `title` and `author`. The optional fields are an integer `year` and a string `isbn` (preserving leading zeros). Omitting either optional field or supplying null stores null, including on replacement. Invalid JSON and invalid fields return 400. Missing books return 404.

```sh
curl -i http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia Butler","year":1979}'
```
