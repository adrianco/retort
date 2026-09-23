# Flow

```mermaid
sequenceDiagram
    Client->>Program.cs: POST /books {title, author, ...}
    Program.cs->>BookInput: Validate()
    BookInput-->>Program.cs: errors (empty)
    Program.cs->>BookRepository: Create(input)
    BookRepository->>SQLite: INSERT ...; SELECT last_insert_rowid()
    SQLite-->>BookRepository: id
    BookRepository->>SQLite: SELECT ... WHERE id
    SQLite-->>BookRepository: row
    BookRepository-->>Program.cs: Book
    Program.cs-->>Client: 201 Created {json}
```

A `POST /books` request is model-bound to a `BookInput` record, validated (title
and author required, year range-checked), then persisted by `BookRepository.Create`,
which opens a fresh `SqliteConnection` per operation, inserts the row, and re-reads
it by `last_insert_rowid()` to return the full `Book`. Each repository method opens
and disposes its own connection; a shared in-memory DB is kept alive by a held
connection when `Mode=Memory` is in the connection string (used by tests). Input
validation and structured 400/404 error bodies are present; there is no pagination,
auth, or ISBN-format validation.
