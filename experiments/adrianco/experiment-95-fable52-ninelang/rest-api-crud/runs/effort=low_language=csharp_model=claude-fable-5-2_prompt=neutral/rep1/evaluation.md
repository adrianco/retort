# Evaluation: effort=low_language=csharp_model=claude-fable-5-2_prompt=neutral · rep 1

## Summary

- **Factors:** language=csharp, model=claude-fable-5-2, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 14 passed / 0 failed / 0 skipped (14 effective — 9 `[Fact]` + 1 `[Theory]` with 5 cases)
- **Build:** pass — from `scores.json` (`test_coverage=1.0` ⇒ build + all tests passed)
- **Lint:** pass — `code_quality=1.0` from `scores.json`
- **Architecture:** minimal-API single-file app + repository; see Metrics
- **Findings:** 0 items in `findings.jsonl`

Clean run. ASP.NET Core minimal API (.NET 10) with a `BookRepository` over `Microsoft.Data.Sqlite`,
parameterized SQL throughout, problem-details error bodies, and an in-process `WebApplicationFactory`
integration test suite backed by a fresh temp SQLite file per test.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `Program.cs:16-22`, `BookRepository.cs:60-71`; 201 + Location |
| R2 | GET /books lists all books | ✓ implemented | `Program.cs:24`, `BookRepository.cs:33-48` |
| R3 | GET /books ?author= filter | ✓ implemented | `BookRepository.cs:38-42` (`WHERE author = $author COLLATE NOCASE`); test `List_...FiltersByAuthor` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `Program.cs:26-27`, `BookRepository.cs:50-58`; `Get_UnknownId_Returns404` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `Program.cs:29-34`, `BookRepository.cs:73-83`; `Update_ReplacesBook` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `Program.cs:36-37`, `BookRepository.cs:85-92`; `Delete_RemovesBook_ThenReturns404` |
| R7 | Data stored in SQLite | ✓ implemented | `BookRepository.cs:1,14-23` (CREATE TABLE in SQLite) |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201/200/204/404/400 across `Program.cs`; `NotFound` → problem-details 404 |
| R9 | Input validation: title & author required | ✓ implemented | `Models.cs:8-14`, `Program.cs:18-19,31-32`; `Create_MissingTitleOrAuthor_Returns400` |
| R10 | GET /health | ✓ implemented | `Program.cs:14`; `Health_ReturnsOk` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — Run, Test, Endpoints, Example |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | `BooksApiTests.cs` — 14 effective test cases |

## Build & Test

```text
# Not re-run — stored mechanical scores from scores.json
test_coverage = 1.0   # build + all tests passed
code_quality  = 1.0
defect_rate   = 1.0
```

Skip scan (`grep -rE "Skip\s*=|Skip\(" tests --include="*.cs"`): 0 skipped/disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, .cs) | 314 |
| Source files (.cs) | 4 |
| Dependencies (test proj refs) | Microsoft.Data.Sqlite, Mvc.Testing, NET.Test.Sdk, xunit, xunit.runner.visualstudio |
| Tests total | 14 (9 Fact + 5 Theory cases) |
| Tests effective | 14 |
| Skip ratio | 0% |
| Build/Lint | pass (test_coverage=1.0, code_quality=1.0) |

Extras beyond spec (not deductions): malformed-JSON → 400 test, case-insensitive author filter,
optional-fields-omitted test, parameterized SQL (injection-safe), per-test DB isolation with pool cleanup.

## Findings

None. All 12 pinned requirements implemented and exercised by tests; no skipped tests; clean mechanical scores.

## Reproduce

```bash
cd experiments/adrianco/experiment-95-fable52-ninelang/rest-api-crud/runs/effort=low_language=csharp_model=claude-fable-5-2_prompt=neutral/rep1
cat scores.json
grep -rE "\[Fact\]|\[Theory\]" tests --include="*.cs" | wc -l
grep -rE "Skip\s*=|Skip\(" tests --include="*.cs" | wc -l
```
