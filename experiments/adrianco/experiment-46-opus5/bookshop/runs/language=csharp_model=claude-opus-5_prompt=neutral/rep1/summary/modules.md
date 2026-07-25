# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/BookApi/Program.cs | App bootstrap: DI, SQLite DbContext, EnsureCreated, endpoint mapping | top-level statements, `public partial class Program` |
| src/BookApi/Endpoints/BookEndpoints.cs | CRUD route handlers for /books | `MapBookEndpoints()` |
| src/BookApi/Endpoints/HealthEndpoints.cs | /health route that probes DB connectivity | `MapHealthEndpoint()` |
| src/BookApi/Models/Book.cs | EF entity for a stored book | `Book` |
| src/BookApi/Contracts/Contracts.cs | Request/response DTOs | `BookRequest`, `BookResponse` |
| src/BookApi/Data/BookDbContext.cs | EF Core DbContext + model config (unique ISBN, author index) | `BookDbContext`, `Books` |
| src/BookApi/Validation/BookRequestValidator.cs | Field validation + normalization | `BookRequestValidator.TryValidate()`, `ValidatedBook` |
| src/BookApi/Validation/Isbn.cs | ISBN-10/13 normalization + checksum | `Isbn.TryNormalize()` |
| tests/BookApi.Tests/BooksEndpointTests.cs | HTTP integration tests via WebApplicationFactory | 18 Fact/Theory (CRUD, filter, health, validation, ISBN conflict) |
| tests/BookApi.Tests/BookRequestValidatorTests.cs | Unit tests for validator | 9 Fact/Theory |
| tests/BookApi.Tests/IsbnTests.cs | Unit tests for ISBN normalization | 2 Theory |
| tests/BookApi.Tests/BookApiFactory.cs | Test host wiring (isolated SQLite per run) | `BookApiFactory` |
