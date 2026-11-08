# Evaluation: effort=low_language=csharp_model=claude-haiku-5-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=csharp, model=claude-haiku-5-5, prompt=neutral, effort=low (repair run)
- **Status:** ok — all 12 pinned requirements implemented; build + tests pass
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 9 passed / 0 failed / 0 skipped (9 effective)
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build + all tests ran)
- **Lint:** pass — code_quality=1.0 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

This was a REPAIR task (`TASK.md` begins "# REPAIR TASK"): a prior attempt failed because "the build/tests did not fully pass" (`FEEDBACK.md`). The repaired workspace now builds and all tests pass, and every requirement is satisfied.

## Requirements

Checklist is the pinned `REQUIREMENTS.json` (12 items, constant denominator across runs).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `Program.cs:17-27`; `BookRepository.Add` |
| R2 | GET /books lists all | ✓ implemented | `Program.cs:29-30`; `BookRepository.List` |
| R3 | GET /books ?author= filter | ✓ implemented | `BookRepository.cs:69-73` WHERE author COLLATE NOCASE; test `List_FiltersByAuthor_CaseInsensitively` |
| R4 | GET /books/{id} by id (404) | ✓ implemented | `Program.cs:32-36`; test `GetById_UnknownBook_ReturnsNotFound` |
| R5 | PUT /books/{id} updates | ✓ implemented | `Program.cs:38-48`; test `Update_ExistingBook_ReturnsUpdatedBook` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `Program.cs:50-51`; test `Delete_ThenGet_ReturnsNotFound` |
| R7 | Data stored in SQLite | ✓ implemented | `BookRepository.cs:1,12-21` Microsoft.Data.Sqlite, CREATE TABLE books |
| R8 | JSON + correct status codes | ✓ implemented | `Program.cs` Results.Created/Ok/NotFound/NoContent/ValidationProblem |
| R9 | Validation: title+author required | ✓ implemented | `Book.cs:23-30`; test `Create_WithMissingTitleOrAuthor_ReturnsBadRequest` |
| R10 | GET /health | ✓ implemented | `Program.cs:12-15`; test `Health_ReturnsHealthy` |
| R11 | README with setup/run | ✓ implemented | `README.md` — prerequisites, run, test, endpoints, examples |
| R12 | ≥ 3 tests that run | ✓ implemented | `tests/BookApi.Tests/BooksApiTests.cs` — 9 `[Fact]`, test_coverage=1.0 |

Enhancements beyond spec (not deductions): year-range + ISBN-format validation (`Book.cs:33-50`), DB-reachability health check returning 503 (`Program.cs:12-15`).

## Build & Test

Scores read from `scores.json` (mechanical scorers already ran — build/test not re-run per skill guidance):

```text
test_coverage = 1.0   → build succeeded AND all tests ran and passed
code_quality  = 1.0
defect_rate   = 1.0   → build+test succeeded
maintainability = 0.909
idiomatic     = 0.85
token_efficiency = 0.0367
```

```text
# tests: tests/BookApi.Tests/BooksApiTests.cs
9 [Fact] integration tests via WebApplicationFactory<Program> on a throwaway per-test SQLite file
0 skipped / 0 disabled
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + tests, .cs excl obj/bin) | 412 |
| Source .cs files | 4 (3 app + 1 test file) |
| Dependencies (PackageReference, app + test) | 7 |
| Tests total | 9 |
| Tests effective | 9 |
| Skip ratio | 0% |
| Build | pass (test_coverage=1.0) |

## Findings

Top findings (full list in `findings.jsonl`) — all informational, no defects:

1. [info] Validation exceeds the spec (year range + ISBN format) — `Book.cs:33-50`
2. [info] Health check verifies DB reachability, not just liveness — `Program.cs:12-15`
3. [info] ?author= filter is case-insensitive exact match, not substring — `BookRepository.cs:70-72`

## Reproduce

```bash
cd experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=csharp_model=claude-haiku-5-5_prompt=neutral/rep1
cat scores.json                     # mechanical scores (build/test/lint already computed)
grep -rE "\[Fact\]|\[Theory\]" tests/BookApi.Tests/BooksApiTests.cs | wc -l   # test count
grep -rE "Skip\s*=|Skip\(" --include="*.cs" tests | grep -v /obj/ | grep -v /bin/ | wc -l  # skips = 0
# full build+test (optional, slow): dotnet test tests/BookApi.Tests/BookApi.Tests.csproj
```
