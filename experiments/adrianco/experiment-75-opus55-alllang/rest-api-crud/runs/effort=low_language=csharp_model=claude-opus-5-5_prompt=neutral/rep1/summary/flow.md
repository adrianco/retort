# Flow

```mermaid
sequenceDiagram
    Client->>Program.cs: POST /books {title, author, year, isbn}
    Program.cs->>BookInput: Validate()
    BookInput-->>Program.cs: errors (empty on success)
    Program.cs->>BookRepository: Create(input)
    BookRepository->>SQLite: INSERT ...; SELECT last_insert_rowid()
    SQLite-->>BookRepository: new id
    BookRepository->>SQLite: SELECT ... WHERE id
    SQLite-->>BookRepository: row
    BookRepository-->>Program.cs: Book
    Program.cs-->>Client: 201 Created {json}
```

A `POST /books` request is bound to `BookInput`, validated (title and author required, year range-checked); on failure it returns `400` via `Results.ValidationProblem`. On success `BookRepository.Create` opens a fresh SQLite connection, inserts the row, re-reads it by `last_insert_rowid()`, and the handler returns `201 Created` with a `Location` header and the JSON body. Persistence is real SQLite (file-backed by default, shared in-memory under test). A connection is opened per repository call rather than pooled; parameterised SQL is used throughout.
