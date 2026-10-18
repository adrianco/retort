# Evaluation: agent=codex_effort=low_language=csharp_model=gpt-6-luna_prompt=neutral · rep 2

## Summary

- **Factors:** language=csharp, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective). From scores.json: test_coverage=1.0
- **Build:** pass (inferred from test_coverage=1.0 / defect_rate=1.0 in scores.json; not re-run)
- **Lint:** pass. code_quality=1.0
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 2 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `BooksApi/Program.cs:13` → `BookRepository.CreateAsync`; returns 201 + Location; test `CreateAndGetBook` |
| R2 | GET /books lists all books | ✓ implemented | `Program.cs:20`, `BookRepository.ListAsync` |
| R3 | GET /books supports ?author= | ✓ implemented | `BookRepository.ListAsync` `WHERE Author = $author COLLATE NOCASE`; test `ListsAndFiltersBooksByAuthor` |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `Program.cs:23`; tests `CreateAndGetBook`, `ValidatesRequiredFieldsAndReturnsNotFound` |
| R5 | PUT /books/{id} updates | ✓ implemented | `Program.cs:26`, `BookRepository.UpdateAsync`; test `UpdatesDeletesAndChecksHealth` |
| R6 | DELETE /books/{id} | ✓ implemented | `Program.cs:33` returns 204/404; test `UpdatesDeletesAndChecksHealth` |
| R7 | SQLite storage | ✓ implemented | `Microsoft.Data.Sqlite` in `BookRepository.cs`, `CREATE TABLE IF NOT EXISTS Books` |
| R8 | JSON + correct status codes | ✓ implemented | 201/200/204/404/400 via `Results.*`; README lists them |
| R9 | title and author required (400) | ✓ implemented | `Program.cs:IsValid` (whitespace-aware) on POST and PUT → `ValidationProblem` 400; test `ValidatesRequiredFieldsAndReturnsNotFound` |
| R10 | GET /health | ✓ implemented | `Program.cs:11` → `{status:"healthy"}`; asserted in `UpdatesDeletesAndChecksHealth` |
| R11 | README with setup/run | ✓ implemented | `README.md` covers the SDK, `dotnet run`, connection string override, build/test |
| R12 | ≥3 tests | ✓ implemented | 4 xUnit `[Fact]` integration tests via `WebApplicationFactory`, isolated temp DB |

Prompt factor `neutral` sets no methodology, only "include tests that demonstrate the implementation" — met (P: none checkable beyond R12).

Beyond spec: parameterized SQL throughout, author index, case-insensitive author filter, `{id:int}` route constraints, connection string configurable for test isolation.

## Build & Test

Not re-run (per skill). Stored scores (`scores.json`):

```text
test_coverage=1.0  defect_rate=1.0  code_quality=1.0
maintainability=0.591  idiomatic=0.78  token_efficiency=0.0142
```

The agent itself never saw a green run. Its first `dotnet test` failed to compile (restore race, `IClassFixture`/`Fact` unresolved). Its retry with `--no-restore` built, then vstest aborted with `SocketException (13): Permission denied` in the codex sandbox. The harness scorer ran the suite successfully afterward.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 151 (Program.cs 47, BookRepository.cs 99, Book.cs 5) |
| Test LOC | 79 |
| Files | 4 .cs + 2 .csproj + .sln + README |
| Dependencies | 1 runtime (Microsoft.Data.Sqlite), 4 test |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

All 4 (full list in `findings.jsonl`):

1. [medium] `ListsAndFiltersBooksByAuthor` depends on test order: it shares a DB with `CreateAndGetBook`, which also inserts a "Frank Herbert" book, so `Assert.Single` fails if that test runs first
2. [low] The validation error always names both title and author, even when only one is missing
3. [low] No tests for PUT/DELETE on a missing id, or for PUT with invalid input
4. [info] The codex sandbox blocks vstest's socket, so the agent shipped without a passing local test run

## Reproduce

```bash
cd "<run_dir>"
cat scores.json
cat ../../REQUIREMENTS.json
grep -nE "Skip|\[Fact\]|\[Theory\]" BooksApi.Tests/*.cs
wc -l BooksApi/*.cs BooksApi/*/*.cs BooksApi.Tests/*.cs
```
