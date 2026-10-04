# Evaluation: effort=low_language=csharp_model=claude-opus-5-5_prompt=neutral · rep 2

## Summary

- **Factors:** language=csharp, model=claude-opus-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 15 passed / 0 failed / 0 skipped (15 effective)
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build + tests succeeded)
- **Lint:** pass (code_quality=1.0 from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 0 items in `findings.jsonl` (0 critical, 0 high)

## Requirements

Checklist is the pinned `REQUIREMENTS.json` (12 fixed requirements, comparable across all runs of this task).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `Program.cs:13`; `BookStore.Create` (`BookStore.cs:57`) INSERT…RETURNING; test `Post_CreatesBook_AndGetReturnsIt` |
| R2 | GET /books lists all | ✓ implemented | `Program.cs:23`; `BookStore.List` (`BookStore.cs:28`); test `List_ReturnsAllBooks_AndFiltersByAuthor` |
| R3 | GET /books ?author= filter | ✓ implemented | `BookStore.cs:33-37` `WHERE author = $author COLLATE NOCASE`; test asserts filtered subset |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `Program.cs:25-26` + `NotFound` helper; tests `Post_...GetReturnsIt`, `Get_UnknownId_Returns404` |
| R5 | PUT /books/{id} updates | ✓ implemented | `Program.cs:28`; `BookStore.Update` (`BookStore.cs:72`); tests `Put_UpdatesBook`, `Put_UnknownId_Returns404` |
| R6 | DELETE /books/{id} | ✓ implemented | `Program.cs:37`; `BookStore.Delete` (`BookStore.cs:87`); test `Delete_RemovesBook` |
| R7 | Data stored in SQLite | ✓ implemented | `BookStore.cs:1,11-26` Microsoft.Data.Sqlite, CREATE TABLE + real connections (not in-memory state) |
| R8 | JSON + appropriate status codes | ✓ implemented | `Results.Created/Ok/NoContent/NotFound/ValidationProblem`; codes asserted across tests (201/200/204/404/400) |
| R9 | Validation: title & author required | ✓ implemented | `Book.cs:8-18` `BookInput.Validate()`; test `Post_InvalidInput_Returns400WithFieldError` (5 cases) |
| R10 | GET /health | ✓ implemented | `Program.cs:11`; test `Health_ReturnsOk` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` (318 words, 2.5 KB) |
| R12 | ≥3 unit/integration tests | ✓ implemented | 10 `[Fact]` + 1 `[Theory]`×5 `[InlineData]` = 15 cases; test_coverage=1.0 |

Enhancements beyond spec (not deductions): malformed-JSON → 400 (`Post_MalformedJson_Returns400`), PUT-invalid leaves record unchanged, year-range validation (0–9999), case-insensitive author filter, `Location` header assertion, per-test isolated temp DB with pool cleanup.

## Build & Test

Not re-run — stored mechanical scores are authoritative (per evaluate-run skill).

```text
scores.json: test_coverage=1.0  code_quality=1.0  defect_rate=1.0
             maintainability=0.898  idiomatic=0.9  token_efficiency=0.054
test_coverage=1.0 ⇒ build succeeded AND all tests passed
```

Skip scan (`grep -rE "Skip *=|\[Ignore|Skip\("` over tests/): 0 matches → no skipped/disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, .cs excl obj/bin) | 353 |
| Files (excl obj/bin/.git) | 16 |
| Dependencies | Microsoft.Data.Sqlite (+ Microsoft.AspNetCore.Mvc.Testing for tests) |
| Tests total | 15 |
| Tests effective | 15 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

None. All 12 pinned requirements implemented, build + 15 tests pass, no skipped tests, no lint deductions. `findings.jsonl` is empty.

## Reproduce

```bash
cd "experiments/adrianco/experiment-79-opus55-isolated/rest-api-crud/runs/effort=low_language=csharp_model=claude-opus-5-5_prompt=neutral/rep2"
cat scores.json                                   # stored mechanical scores (authoritative)
cat ../../../REQUIREMENTS.json                    # pinned 12-requirement checklist
grep -rE "Skip *=|\[Ignore|Skip\(" tests/ --include="*.cs" | wc -l   # -> 0
grep -cE "\[Fact\]" tests/BooksApi.Tests/BooksApiTests.cs            # -> 10
grep -cE "\[InlineData" tests/BooksApi.Tests/BooksApiTests.cs        # -> 5
# Optional full rebuild: dotnet test  (net10.0)
```
