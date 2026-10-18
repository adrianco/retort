# Evaluation: effort=low language=csharp model=claude-haiku-5-5 prompt=neutral · rep 3

## Summary

- **Factors:** language=csharp, model=claude-haiku-5-5, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective)
- **Build:** pass — from scores.json (`defect_rate=1.0`, `test_coverage=0.9572`)
- **Lint:** pass — `code_quality=1.0` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info enhancements)

## Requirements

Checklist is the pinned `rest-api-crud/REQUIREMENTS.json` (12 items, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `Program.cs:30` MapPost → `BookRepository.cs:70 CreateAsync` (INSERT) |
| R2 | GET /books lists all | ✓ implemented | `Program.cs:40` MapGet → `BookRepository.cs:37 ListAsync` |
| R3 | GET /books ?author= filter | ✓ implemented | `BookRepository.cs:48` WHERE author = $author COLLATE NOCASE; test `List_filters_by_author_case_insensitively` |
| R4 | GET /books/{id} single, 404 | ✓ implemented | `Program.cs:43` → `GetAsync`; returns NotFound when null; test `Get_missing_book_returns_404` |
| R5 | PUT /books/{id} updates | ✓ implemented | `Program.cs:49` → `BookRepository.cs:85 UpdateAsync` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `Program.cs:59` → `BookRepository.cs:101 DeleteAsync` |
| R7 | Data in SQLite / embedded DB | ✓ implemented | `BookRepository.cs` Microsoft.Data.Sqlite, CREATE TABLE + ADO.NET; csproj package ref |
| R8 | JSON + appropriate status codes | ✓ implemented | `TypedResults` 201/200/404/400/204/503; camelCase JSON (`Program.cs:9`) |
| R9 | Validation: title & author required | ✓ implemented | `Book.cs:38` `BookValidator`; tests `Create_rejects_missing_title_or_author` (4 cases) |
| R10 | GET /health | ✓ implemented | `Program.cs:14` pings DB, 200/503; test `Health_returns_healthy` |
| R11 | README with setup/run | ✓ implemented | `README.md` prerequisites, `dotnet run`, `dotnet test`, endpoint table |
| R12 | ≥3 unit/integration tests | ✓ implemented | `BooksApiTests.cs` 8 test attributes = 11 effective cases; `test_coverage=0.9572` |

## Build & Test

Scores read from `scores.json` (inline gate) — toolchain NOT re-run per skill policy.

```text
scores.json
{"code_quality": 1.0, "token_efficiency": 0.0230, "test_coverage": 0.9572,
 "defect_rate": 1.0, "maintainability": 0.8733, "idiomatic": 0.85}
```

`defect_rate=1.0` ⇒ build + tests succeeded. `test_coverage=0.9572` ⇒ tests executed with 95.7% coverage. `code_quality=1.0` ⇒ clean lint.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 271 (Program 60, Book 59, BookRepository 152) |
| Lines of code (tests) | 160 |
| Source files | 7 (incl. 2 csproj, appsettings) |
| Dependencies | 1 runtime (Microsoft.Data.Sqlite) + 5 test |
| Tests total (effective) | 11 (7 Facts + 1 Theory × 4 InlineData) |
| Skipped tests | 0 |
| Skip ratio | 0% |
| Coverage | 95.72% |

## Findings

No defects. Top items (all info-level enhancements beyond spec):

1. [info] E1 — /health verifies DB reachability (503 on failure), not just liveness
2. [info] E2 — validation extends beyond required title/author (year range, length caps, ISBN)
3. [info] E3 — ?author= filter is case-insensitive (COLLATE NOCASE)

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=csharp_model=claude-haiku-5-5_prompt=neutral/rep3"
cat scores.json                     # stored build/test/lint scores (not re-run)
dotnet test                         # optional: build + run xUnit integration tests
```
