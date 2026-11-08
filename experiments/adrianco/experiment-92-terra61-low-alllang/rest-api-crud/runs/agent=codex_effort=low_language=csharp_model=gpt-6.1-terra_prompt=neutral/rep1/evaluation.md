# Evaluation: rest-api-crud · agent=codex effort=low language=csharp model=gpt-6.1-terra prompt=neutral · rep 1

## Summary

- **Factors:** language=csharp, model=gpt-6.1-terra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build + all tests passed)
- **Lint:** pass — code_quality=1.0 from scores.json
- **Architecture:** minimal ASP.NET Core Minimal API (`Program.cs`) over a SQLite data layer (`BookStore.cs`); `run-summary` not separately invoked (trivial 2-file service)
- **Findings:** 0 items in `findings.jsonl`

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `Program.cs:12` MapPost → `BookStore.cs:Create` INSERT ... RETURNING id |
| R2 | GET /books lists all books | ✓ implemented | `Program.cs:9` MapGet → `BookStore.cs:List` |
| R3 | GET /books ?author= filter | ✓ implemented | `BookStore.cs:List` `WHERE author = $author COLLATE NOCASE`; test `ListFiltersByAuthor` |
| R4 | GET /books/{id} single book | ✓ implemented | `Program.cs:10` returns `Results.NotFound()` when absent |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `Program.cs:19` MapPut → `BookStore.cs:Update` (null→404) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `Program.cs:26` MapDelete → `BookStore.cs:Delete` (204/404) |
| R7 | Data stored in SQLite | ✓ implemented | `BookStore.cs` Microsoft.Data.Sqlite; `CREATE TABLE books`; `BooksApi.csproj` package ref |
| R8 | JSON responses + HTTP status codes | ✓ implemented | `Results.Ok/Created/NotFound/NoContent/ValidationProblem` throughout `Program.cs` |
| R9 | Validation: title and author required | ✓ implemented | `Program.cs:30` `Validate` rejects blank/null; test `ValidationRejectsMissingOrBlankRequiredFields` |
| R10 | GET /health health check | ✓ implemented | `Program.cs:8` returns `{status:"healthy"}` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — Run, API, Tests sections |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | `Tests/ApiTests.cs` — 4 `[Fact]` tests; test_coverage=1.0 |

## Build & Test

Scores read from `scores.json` (computed by retort scorers; not re-run):

```text
test_coverage = 1.0   → build succeeded + all tests passed
code_quality  = 1.0
defect_rate   = 1.0
maintainability = 0.943
idiomatic     = 0.85
```

Test suite: `dotnet test Tests/BooksApi.Tests.csproj` — 4 `[Fact]` integration tests via
`WebApplicationFactory<Program>`, each against an isolated temp SQLite db. No skipped/ignored tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 208 (Program 39, BookStore 92, Tests 77) |
| Files (excl. bin/obj/.git) | 15 |
| Dependencies | api: Microsoft.Data.Sqlite; tests: Mvc.Testing, Test.Sdk, xunit, xunit.runner.visualstudio |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |

## Findings

None. All 12 requirements implemented with test evidence; build + tests pass; no skipped tests;
clean idiomatic Minimal-API implementation. `findings.jsonl` is empty.

## Reproduce

```bash
cd "runs/agent=codex_effort=low_language=csharp_model=gpt-6.1-terra_prompt=neutral/rep1"
cat scores.json
cat ../../../REQUIREMENTS.json
dotnet test Tests/BooksApi.Tests.csproj   # verification only; scores already computed
```
