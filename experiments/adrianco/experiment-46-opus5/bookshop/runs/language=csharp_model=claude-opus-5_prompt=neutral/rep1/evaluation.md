# Evaluation: language=csharp model=claude-opus-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=csharp, model=claude-opus-5, prompt=neutral (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 49 passed / 0 failed / 0 skipped (49 effective)
- **Build:** pass — `Build succeeded`, 0 errors (from `_agent_stdout.log`; defect_rate=1.0 in scores.json)
- **Lint:** pass — 0 warnings in final build (code_quality=1.0 in scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `BookEndpoints.cs:64 CreateBook` → 201 Created |
| R2 | GET /books lists all | ✓ implemented | `BookEndpoints.cs:28 ListBooks` |
| R3 | GET /books ?author= filter | ✓ implemented | `BookEndpoints.cs:35-42` LIKE with wildcard escaping; test `Get_books_lists_everything_and_filters_by_author` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `BookEndpoints.cs:52 GetBook` → Ok/NotFound |
| R5 | PUT /books/{id} updates | ✓ implemented | `BookEndpoints.cs:100 UpdateBook` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `BookEndpoints.cs:138 DeleteBook` → 204 |
| R7 | Data stored in SQLite | ✓ implemented | `Program.cs:11 UseSqlite`; `BookDbContext.cs` |
| R8 | JSON + appropriate status codes | ✓ implemented | `TypedResults` unions (200/201/204/400/404/409); RFC 7807 ProblemDetails |
| R9 | Validation: title & author required | ✓ implemented | `BookRequestValidator.cs:33-51`; test `..._naming_both_fields` |
| R10 | GET /health | ✓ implemented | `HealthEndpoints.cs:10` probes DB, returns healthy/503 |
| R11 | README with setup/run | ✓ implemented | `README.md` (158 lines) |
| R12 | ≥3 tests | ✓ implemented | 29 [Fact]/[Theory] → 49 cases, all passing |

## Build & Test

```text
dotnet build
Build succeeded.
    0 Error(s)   (final build: 0 Warning(s); the transient NU1903 SQLite advisory
    was remediated by upgrading to SQLitePCLRaw.bundle_e_sqlite3 3.0.3)
```

```text
dotnet test
Passed!  - Failed: 0, Passed: 49, Skipped: 0, Total: 49, Duration: 1 s - BookApi.Tests.dll (net10.0)
```

Scores read from `scores.json` (not re-run): test_coverage=0.965, defect_rate=1.0,
code_quality=1.0, maintainability=0.846, idiomatic=0.87.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 1044 (src + tests, excl. obj/bin) |
| Files | 27 (excl. obj/bin/.git) |
| Dependencies | 2 runtime (EF Core Sqlite, SQLitePCLRaw.bundle) + 5 test |
| Tests total | 49 (from 29 Fact/Theory) |
| Tests effective | 49 |
| Skip ratio | 0% |
| Build duration | ~1.4s (from agent log) |

## Findings

Top findings (full list in `findings.jsonl`) — all info-level; no defects:

1. [info] Transient NU1903 SQLite vuln warning was remediated before delivery (csproj pins patched 3.0.3)
2. [info] Enhancement: unique-ISBN enforcement with race-safe 409 (beyond spec)
3. [info] Enhancement: health check actively probes the database (beyond spec)

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-46-opus5/bookshop/runs/language=csharp_model=claude-opus-5_prompt=neutral/rep1
cat scores.json                                             # stored mechanical scores (not re-run)
grep -rE "\[Fact\]|\[Theory\]" tests/ --include="*.cs" | wc -l   # test count
grep -iE "Passed!|Failed!|Build succeeded" _agent_stdout.log     # build/test result
# to actually run: dotnet test   (requires .NET 10 SDK)
```
