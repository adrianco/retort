# Evaluation: effort=low language=csharp model=claude-opus-5-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=csharp, model=claude-opus-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective — 5 `[Fact]` + one 3-case `[Theory]`)
- **Build:** pass — from `test_coverage=1.0` in scores.json (build + all tests passed)
- **Lint:** pass — `code_quality=0.9556` from scores.json; no skips/disabled tests
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

Mechanical scores read from `scores.json` (inline gate; not re-run): `test_coverage=1.0`, `defect_rate=1.0`, `maintainability=1.0`, `code_quality=0.9556`, `idiomatic=0.72`, `token_efficiency=0.0128`.

## Requirements

Checklist is the pinned `rest-api-crud/REQUIREMENTS.json` (12 fixed items), used verbatim.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `Program.cs:10` handler → `BookRepository.Create` `Program.cs:80` |
| R2 | GET /books lists all books | ✓ implemented | `Program.cs:18` → `List(null)` `Program.cs:88` |
| R3 | GET /books ?author= filter | ✓ implemented | `Program.cs:91` `WHERE author = $a COLLATE NOCASE`; test `List_FiltersByAuthor` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `Program.cs:20` returns `Ok`/`NotFound` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `Program.cs:23` → `Update` `Program.cs:108`; test `Update_ChangesBook_And404ForMissing` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `Program.cs:30` → `Delete` `Program.cs:116`; test `Delete_RemovesBook` |
| R7 | Data stored in SQLite | ✓ implemented | `Microsoft.Data.Sqlite`; `CREATE TABLE books` `Program.cs:63` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `Results.Created/Ok/NotFound/NoContent/ValidationProblem` throughout |
| R9 | Validation: title and author required | ✓ implemented | `BookInput.Validate()` `Program.cs:42-43`; test `Create_MissingRequiredFields_Returns400` |
| R10 | GET /health health-check | ✓ implemented | `Program.cs:8` returns `{status:"ok"}`; test `Health_ReturnsOk` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — run/test/endpoints documented |
| R12 | At least 3 unit/integration tests | ✓ implemented | 6 test methods in `BooksApiTests.cs`; `test_coverage=1.0` |

## Build & Test

Not re-run — mechanical scores taken from the inline gate in `scores.json`:

```text
scores.json: test_coverage=1.0  defect_rate=1.0  maintainability=1.0
=> build succeeded and all tests passed (dotnet test)
```

```text
Test suite: tests/BookApi.Tests/BooksApiTests.cs
  Health_ReturnsOk .............. covers R10
  Create_ThenGet_ReturnsBook .... covers R1, R4
  Create_MissingRequiredFields_Returns400 [Theory x3] .. covers R9
  List_FiltersByAuthor .......... covers R2, R3
  Update_ChangesBook_And404ForMissing .. covers R5 (+404)
  Delete_RemovesBook ............ covers R6 (+404)
  Skips/disabled: 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 208 (`Program.cs` 125, tests 83) |
| Files | 14 (excl. obj/bin/.git) |
| Dependencies | app: 1 (`Microsoft.Data.Sqlite`); tests: 4 |
| Tests total | 8 (5 `[Fact]` + 3-case `[Theory]`) |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; gate scores used) |

## Findings

Top items by severity (full list in `findings.jsonl`) — no critical/high/medium/low; 3 info-level:

1. [info] Validation goes beyond spec (year range check) — `Program.cs:44`
2. [info] Case-insensitive author filter — `Program.cs:91`
3. [info] New SQLite connection opened per repository call — `Program.cs:66`

## Reproduce

```bash
cd "experiments/adrianco/experiment-75-opus55-alllang/rest-api-crud/runs/effort=low_language=csharp_model=claude-opus-5-5_prompt=neutral/rep1"
cat scores.json                       # mechanical gate scores (build+test not re-run)
cat ../../../REQUIREMENTS.json        # pinned 12-item checklist
grep -rcE "\[Fact\]|\[Theory\]" tests --include="*.cs"
grep -rnE "Skip *=|\[Ignore\]|Assert\.Ignore" tests --include="*.cs"   # 0 skips
```
