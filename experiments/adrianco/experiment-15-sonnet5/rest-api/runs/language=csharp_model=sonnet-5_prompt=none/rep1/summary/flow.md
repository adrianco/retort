# Flow

```mermaid
sequenceDiagram
    Client->>Program.cs: POST /books {title, author, year, isbn}
    Program.cs->>Program.cs: Validate(request)
    alt validation fails
        Program.cs-->>Client: 400 ValidationProblem
    else valid
        Program.cs->>BookDbContext: Books.Add(book)
        Program.cs->>BookDbContext: SaveChangesAsync()
        BookDbContext-->>Program.cs: book.Id assigned
        Program.cs-->>Client: 201 Created + Location
    end
```

A `POST /books` request is model-bound to `BookRequest`, validated via DataAnnotations (`Validate()` → `Validator.TryValidateObject`); on failure it returns `400` with a `ValidationProblem` error dictionary. On success the DTO is mapped to a `Book` entity, added to `BookDbContext`, and persisted to SQLite via `SaveChangesAsync()`, then returned as `201 Created` with a `Location` header pointing at `/books/{id}`. Async EF Core access throughout; validation runs before any DB access. The `?author=` filter on `GET /books` uses `Contains` (case-sensitive substring, translated to SQL LIKE).
