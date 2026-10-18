# Flow

```mermaid
sequenceDiagram
    Client->>Program.cs: POST /books {title, author, year, isbn}
    Program.cs->>Program.cs: IsValid(input)?
    Program.cs->>BookRepository: CreateAsync(input)
    BookRepository->>SQLite: INSERT ... ; SELECT last_insert_rowid()
    SQLite-->>BookRepository: new id
    BookRepository-->>Program.cs: Book
    Program.cs-->>Client: 201 Created + {book}
```

A `POST /books` request is first validated (`IsValid` requires non-blank title and author); on failure it returns `400` via `Results.ValidationProblem`. On success the handler calls `BookRepository.CreateAsync`, which opens a fresh `SqliteConnection`, inserts the row with parameterised values, reads back `last_insert_rowid()`, and returns the materialised `Book`. The handler responds `201 Created` with a `/books/{id}` location header. Each repository method opens and disposes its own connection (no pooled shared connection). Input is parameterised throughout (no SQL injection); `?author=` filtering uses `COLLATE NOCASE` with a trimmed value.
