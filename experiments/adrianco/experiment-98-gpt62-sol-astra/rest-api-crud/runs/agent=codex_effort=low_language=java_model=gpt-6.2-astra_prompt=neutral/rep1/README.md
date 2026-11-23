# Book collection API

Install JDK 17 or later and Maven 3.8 or later. From this directory, run:

```sh
mvn package
mvn org.codehaus.mojo:exec-maven-plugin:3.5.0:java -Dexec.mainClass=BookApi
```

The first command runs the request-handler and SQLite integration tests and builds the project. Use `mvn test` to run the tests separately. The service uses the JDK HTTP server and SQLite JDBC. It listens on port 8080 and stores books in `books.db` in the working directory. Set `PORT` or `BOOK_DB` to override those defaults.

| Method | Path | Success |
|---|---|---|
| POST | /books | 201 with the created book and a Location header |
| GET | /books | 200 with an array ordered by ID |
| GET | /books?author=Octavia%20Butler | 200 with exact, case-sensitive author matches |
| GET | /books/{id} | 200 with the book |
| PUT | /books/{id} | 200 with the replacement book |
| DELETE | /books/{id} | 204 with an empty body |
| GET | /health | 200 with a JSON status |

Create a book with:

```sh
curl -i http://localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Dawn","author":"Octavia Butler","year":1987,"isbn":"0446514152"}'
```

POST and PUT require nonblank strings for title and author. Year is an optional 32-bit integer. ISBN is an optional string. Omitted or null optional fields are stored as null, including on replacement. Invalid input returns 400 and missing books return 404.
