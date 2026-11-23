# Book Collection API

Requires Java 17 or later and Maven 3.6.3 or later. SQLite runs embedded and needs no separate installation.

```sh
mvn clean verify
java -jar target/book-api-1.0.0.jar
```

The service listens at `http://localhost:8080` and creates `books.db` in the working directory. Set `SERVER_PORT` to change the port or `SPRING_DATASOURCE_URL` to change the database location, for example `jdbc:sqlite:/path/to/books.db`.

| Method and path | Success | Behavior |
| --- | --- | --- |
| `GET /health` | 200 | Returns `{"status":"UP"}`. |
| `POST /books` | 201 | Returns the created book and its URL in the `Location` header. |
| `GET /books` | 200 | Returns an array ordered by ID. Use `?author=` for an exact, case-sensitive match. |
| `GET /books/{id}` | 200 | Returns the book. |
| `PUT /books/{id}` | 200 | Replaces the book's fields and returns the updated book. |
| `DELETE /books/{id}` | 204 | Deletes the book and returns an empty body. |

Send JSON with nonblank string fields `title` and `author`. The integer `year` and string `isbn` are optional and default to null on create or replacement. SQLite assigns a numeric `id`. Invalid requests receive 400. Requests for missing books receive 404.

```sh
curl -i http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia E. Butler","year":1979,"isbn":"9780807083697"}'
```
