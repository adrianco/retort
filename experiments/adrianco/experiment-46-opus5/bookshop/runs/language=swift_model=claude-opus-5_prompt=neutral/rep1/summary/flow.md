# Flow

```mermaid
sequenceDiagram
    Client->>BookController: POST /books {title,author,year,isbn}
    BookController->>BookRequest: decode + validated()
    BookRequest-->>BookController: ValidatedBook (or Abort 400)
    BookController->>Book: save(on: db)
    Book->>SQLite: INSERT
    SQLite-->>Book: id
    BookController-->>Client: 201 {json} + Location: /books/{id}
```

A `POST /books` request decodes into a lenient `BookRequest`, then `validated()`
trims and checks the payload — required `title`/`author`, an in-range `year`, and
a well-shaped ISBN — throwing `Abort(.badRequest)` that aggregates every problem.
On success a `Book` Fluent model is persisted to the file-backed SQLite database,
and the handler returns `201 Created` with the JSON body and a `Location` header.
Notable: validation aggregates all errors into one message; PUT uses full-replace
semantics (omitted optional fields are cleared); the ISBN check validates shape
only, not the check digit.
