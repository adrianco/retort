# Flow

```mermaid
sequenceDiagram
    Client->>Program.cs: POST /books {title,author,year,isbn}
    Program.cs->>Program.cs: Validate(input)
    alt title/author missing
        Program.cs-->>Client: 400 ValidationProblem
    else valid
        Program.cs->>BookDbContext: Books.Add(book); SaveChangesAsync()
        BookDbContext-->>Program.cs: persisted book (Id assigned)
        Program.cs-->>Client: 201 Created {book}
    end
```

A `POST /books` request is bound to a `BookInput` record, then passed through
`Validate()` which rejects blank `title` or `author` with a 400 validation-problem
response. On success the handler trims the fields, adds a `Book` to the EF Core
`BookDbContext`, persists via `SaveChangesAsync()`, and returns `201 Created` with a
`Location` header pointing at `/books/{id}` and the serialized book. Persistence is
SQLite through EF Core; the schema is created at startup via `EnsureCreated()`.
Handlers are async; error paths (missing id → 404) are handled on every read/write route.
