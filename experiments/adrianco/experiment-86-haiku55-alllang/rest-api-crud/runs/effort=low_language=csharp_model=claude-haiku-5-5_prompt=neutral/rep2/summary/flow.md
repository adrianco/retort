# Flow

```mermaid
sequenceDiagram
    Client->>Program.cs: POST /books {title, author, year, isbn}
    Program.cs->>BookValidator: Validate(input)
    BookValidator-->>Program.cs: errors (empty)
    Program.cs->>SqliteBookRepository: CreateAsync(input)
    SqliteBookRepository->>SQLite: INSERT ... ; last_insert_rowid()
    SQLite-->>SqliteBookRepository: new id
    SqliteBookRepository-->>Program.cs: Book
    Program.cs-->>Client: 201 Created, Location /books/{id}, {json}
```

A `POST /books` is validated by `BookValidator` first; on any error the handler short-circuits to a 400 `ValidationProblem` with a field-level `errors` map. On success `SqliteBookRepository.CreateAsync` opens a fresh connection, inserts the trimmed title/author plus optional year and normalized ISBN (hyphens/spaces stripped), reads back `last_insert_rowid()`, and the handler returns `201 Created` with a `Location` header. Each repository call opens and disposes its own connection (no pooled/shared connection held). Persistence is real SQLite; the schema is created on repository construction.
