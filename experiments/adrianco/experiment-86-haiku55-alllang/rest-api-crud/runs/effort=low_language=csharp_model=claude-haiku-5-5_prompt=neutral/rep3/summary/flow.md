# Flow

```mermaid
sequenceDiagram
    Client->>Program.cs: POST /books {title,author,year,isbn}
    Program.cs->>BookValidator: Validate(request)
    BookValidator-->>Program.cs: errors (empty = valid)
    Program.cs->>SqliteBookRepository: CreateAsync(request)
    SqliteBookRepository->>SQLite: INSERT ... ; SELECT last_insert_rowid()
    SQLite-->>SqliteBookRepository: new id
    SqliteBookRepository-->>Program.cs: Book
    Program.cs-->>Client: 201 Created, Location /books/{id}, JSON body
```

A `POST /books` request is first validated by `BookValidator` (title and author required, length and year-range bounds). On validation failure the handler returns `400 ValidationProblem`; otherwise it calls `SqliteBookRepository.CreateAsync`, which opens a fresh async SQLite connection, inserts the row, reads back the autoincrement id, and returns a `Book` record. The handler responds `201 Created` with a `Location` header and the JSON body. Persistence is real SQLite via ADO.NET (a table is created on startup); all handlers are async and pass `CancellationToken` through. No authentication layer (not required by the spec).
