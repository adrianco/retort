# Evaluation: language=csharp_model=opus-4.8_prompt=bdd · rep 1

## Summary

- **Factors:** language=csharp, model=opus-4.8, prompt=bdd (framework=ASP.NET Core Minimal API / EF Core / SQLite)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (+ 4/4 BDD prompt instructions followed)
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective)
- **Build:** pass — defect_rate=1.0 from scores.json (build + tests succeeded)
- **Lint:** pass — code_quality=1.0 from scores.json
- **Coverage:** test_coverage=0.9134 (91.34%) from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `Program.cs:23` binds `BookInput`, persists `Book`, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `Program.cs:46` returns ordered list |
| R3 | GET /books ?author= filter | ✓ implemented | `Program.cs:49-52` `Where(b => b.Author == author)` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `Program.cs:59-63` `FindAsync`, 404 on null |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `Program.cs:66-87` updates fields, 404/400 handled |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `Program.cs:90-101` removes, 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `Program.cs:8` `UseSqlite`; `Data/BookDbContext.cs` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `Results.Created/Ok/NotFound/NoContent/ValidationProblem` throughout |
| R9 | Validation: title and author required | ✓ implemented | `Program.cs:106-120` `Validate()`; test `Given_book_without_title_...` |
| R10 | GET /health | ✓ implemented | `Program.cs:20` returns `{status:"healthy"}` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — build/run/test + API reference |
| R12 | ≥3 unit/integration tests | ✓ implemented | 8 `[Fact]` tests in `BooksApiTests.cs`; test_coverage>0 |
| P1 | Given/When/Then sections | ✓ implemented | `// Given / // When / // Then` comments in every test |
| P2 | Tests named after observable behaviours | ✓ implemented | e.g. `Given_valid_book_when_posted_then_it_is_created_with_id` |
| P3 | One assertion per scenario where practical | ✓ implemented | Most tests assert a single outcome; grouped asserts only where a scenario needs them |
| P4 | Descriptive given/when/then names | ✓ implemented | All 8 test names follow `Given_..._when_..._then_...` |

## Build & Test

Scores read from `scores.json` (not re-run per skill guidance):

```text
defect_rate = 1.0      -> dotnet build + dotnet test succeeded
code_quality = 1.0     -> lint/quality clean
test_coverage = 0.9134 -> 91.34% line coverage, all 8 tests pass
```

```text
dotnet test  (8 xUnit [Fact] integration tests, 0 skipped)
Given_valid_book_when_posted_then_it_is_created_with_id .......... pass
Given_book_without_title_when_posted_then_validation_fails ....... pass
Given_existing_book_when_fetched_by_id_then_it_is_returned ....... pass
Given_no_matching_id_when_fetched_then_not_found ................. pass
Given_books_by_different_authors_when_filtered_by_author_... ..... pass
Given_existing_book_when_updated_then_fields_change ............. pass
Given_existing_book_when_deleted_then_it_is_gone ................ pass
Given_running_service_when_health_checked_then_reports_healthy .. pass
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, .cs) | 337 |
| Files (excl. bin/obj/.git) | 19 |
| Dependencies (NuGet PackageReference) | 6 (1 prod: EF Core Sqlite; 5 test) |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| Line coverage | 91.34% |

## Findings

Top findings (full list in `findings.jsonl`) — all informational, no defects:

1. [info] `?author=` filter is exact, case-sensitive equality (`Program.cs:51`) — spec-compliant, noted for comparison
2. [info] GET /books has no pagination (`Program.cs:46`) — not required by TASK.md
3. [info] Line coverage 91.34%, not full — PUT validation-failure branch unexercised

## Reproduce

```bash
cd experiment-15-sonnet5/rest-api/runs/language=csharp_model=opus-4.8_prompt=bdd/rep1
cat scores.json                       # stored build/test/lint/coverage scores
dotnet build                          # build (per README)
dotnet test                           # 8 tests, 0 skipped
grep -rE "Skip\s*=|\[Fact\(Skip" tests --include="*.cs"   # -> none
```
