# Book collection API

Requires Java 17 or later and Maven 3. Run `mvn test` to run the tests, and `mvn spring-boot:run` to start the service on port 8080. Alternatively, build with `mvn package` and run `java -jar target/books-1.0.0.jar`.

SQLite data persists in `books.db` in the working directory. Set `BOOKS_DB_URL` to a JDBC SQLite URL (for example `jdbc:sqlite:/path/to/books.db`) to choose another database. Set `SERVER_PORT` to change the port.

- `POST /books` creates a book and returns 201 and a Location header.
- `GET /books` lists books; `?author=...` filters by exact, case-sensitive author.
- `GET /books/{id}` returns a book.
- `PUT /books/{id}` replaces a book's fields.
- `DELETE /books/{id}` deletes a book and returns 204.
- `GET /health` returns `{"status":"ok"}`.

Create and update accept JSON such as `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`. Title and author must be nonblank strings; year (an integer) and isbn (a string) are optional and can be null. Missing books return 404, and invalid inputs return 400. ISBN is a string to preserve leading zeroes.
