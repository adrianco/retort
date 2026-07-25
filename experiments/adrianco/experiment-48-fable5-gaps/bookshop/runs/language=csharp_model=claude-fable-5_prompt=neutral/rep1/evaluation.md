# Evaluation: language=csharp_model=claude-fable-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=csharp, model=claude-fable-5, prompt=neutral (agent/framework unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective)
- **Build:** pass (from `test_coverage=0.9925`, `defect_rate=1.0` in scores.json — build + tests succeeded)
- **Lint:** pass — `code_quality=1.0` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

Checklist pinned from `bookshop/REQUIREMENTS.json` (R1–R12), used verbatim. The `prompt=neutral` factor (`prompts/neutral.md`) prescribes no methodology and adds no checkable instructions, so there are no `P*` requirements.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `BookApi/Program.cs` MapPost `/books` → `repo.Create`; test `CreateBook_ReturnsCreatedWithLocationAndBody` |
| R2 | GET /books lists all books | ✓ implemented | `Program.cs` MapGet `/books` → `repo.List`; test `ListBooks_FiltersByAuthor` asserts full list |
| R3 | GET /books ?author= filter | ✓ implemented | `BookRepository.cs:List` adds `WHERE author = $author COLLATE NOCASE`; test asserts 2 filtered results |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `Program.cs` MapGet `/books/{id:long}`; tests `GetBook_ReturnsBook`, `GetBook_UnknownId_ReturnsNotFound` |
| R5 | PUT /books/{id} updates | ✓ implemented | `Program.cs` MapPut → `repo.Update`; tests `UpdateBook_ReplacesFields`, `UpdateBook_UnknownId_ReturnsNotFound` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `Program.cs` MapDelete → `repo.Delete` (204/404); tests `DeleteBook_RemovesBook`, `DeleteBook_UnknownId_ReturnsNotFound` |
| R7 | Data in SQLite | ✓ implemented | `BookRepository.cs` uses `Microsoft.Data.Sqlite`; CREATE TABLE books; `BookApi.csproj` references Sqlite + `SQLitePCLRaw.bundle_e_sqlite3` |
| R8 | JSON responses + correct status codes | ✓ implemented | `Results.Created/Ok/NoContent/BadRequest/NotFound` across handlers; tests assert 201/200/204/400/404 |
| R9 | Validation: title + author required | ✓ implemented | `Book.cs:BookInput.Validate()`; test `CreateBook_MissingTitleAndAuthor_ReturnsBadRequest`, `UpdateBook_InvalidInput_ReturnsBadRequest` |
| R10 | GET /health | ✓ implemented | `Program.cs` MapGet `/health` → `{status:"ok"}`; test `Health_ReturnsOk` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — layout, requirements, run command, connection-string override |
| R12 | ≥ 3 tests | ✓ implemented | 11 `[Fact]` xUnit integration tests in `BookApi.Tests/BookApiTests.cs` |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate output):

```text
test_coverage = 0.9925   # build + all tests passed (coverage-weighted, not a test failure)
defect_rate   = 1.0      # build + test succeeded
code_quality  = 1.0
idiomatic     = 0.93
```

Test suite: `dotnet test` — 11 xUnit integration tests via `WebApplicationFactory<Program>`, each with an isolated temp SQLite DB. 0 skipped (`grep Skip` → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Source files (excl. bin/obj) | 9 |
| Dependencies (BookApi) | 2 (Microsoft.Data.Sqlite, SQLitePCLRaw.bundle_e_sqlite3) |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| test_coverage | 0.9925 |
| code_quality | 1.0 |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] ISBN format/uniqueness not validated — beyond spec (`Book.cs`)
2. [info] Empty `?author=` edge case untested (`BookRepository.cs:List`)

No critical, high, medium, or low findings. This is a clean, fully-conformant run.

## Reproduce

```bash
cd runs/language=csharp_model=claude-fable-5_prompt=neutral/rep1
cat scores.json                       # mechanical scores (build/test/lint) — no re-run
grep -rEc "Skip|Ignore" BookApi.Tests/*.cs   # skip count = 0
# optional full build+test:
dotnet test BookCollection.slnx
```
