# Flow

```mermaid
sequenceDiagram
    Client->>handlers.go: POST /books {title,author,...}
    handlers.go->>handlers.go: decodeBook (MaxBytes, trim, validate)
    alt invalid
        handlers.go-->>Client: 422 {error,fields}
    else valid
        handlers.go->>store.go: Store.Create(b)
        store.go->>SQLite: INSERT INTO books
        SQLite-->>store.go: LastInsertId
        store.go-->>handlers.go: Book{ID,...}
        handlers.go-->>Client: 201 + Location {json}
    end
```

A `POST /books` request is size-capped (1 MiB via `http.MaxBytesReader`), JSON-decoded with strict trailing-data rejection, and validated: `title`/`author` must be non-blank and `year` in 0–9999, else `422` with a `fields` map. Valid input is inserted into SQLite and returned as `201` with a `Location` header. Notable: validation failures return `422 Unprocessable Entity` rather than `400`; a single DB connection (`SetMaxOpenConns(1)`) serialises writes; graceful shutdown on SIGINT/SIGTERM.
