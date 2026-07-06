# Evaluation: language=csharp_model=sonnet-5_prompt=bdd · rep 1

## Summary

- **Factors:** language=csharp, model=sonnet-5, prompt=bdd
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (+1 prompt instruction P1 followed)
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective)
- **Build:** pass (defect_rate=1.0 from retort.db; test_coverage=0.9787 ⇒ build + tests ran)
- **Lint:** pass — 1 build advisory (NU1903, non-blocking); code_quality=1.0 from retort.db
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `Controllers/BooksController.cs:20-36` CreateBook, persists + 201 |
| R2 | GET /books lists all | ✓ implemented | `BooksController.cs:38-50` ListBooks |
| R3 | GET /books ?author= filter | ✓ implemented | `BooksController.cs:43-46` `Where(b => b.Author.Contains(author))` |
| R4 | GET /books/{id} + 404 | ✓ implemented | `BooksController.cs:52-62` GetBook returns NotFound when null |
| R5 | PUT /books/{id} updates | ✓ implemented | `BooksController.cs:64-81` UpdateBook |
| R6 | DELETE /books/{id} | ✓ implemented | `BooksController.cs:83-96` DeleteBook → 204 |
| R7 | Data stored in SQLite | ✓ implemented | `Program.cs:8` UseSqlite; `Data/BookDbContext.cs` |
| R8 | JSON + correct status codes | ✓ implemented | 201/200/404/204 in controller; `[ApiController]` auto-400 |
| R9 | Validation: title+author required | ✓ implemented | `Dtos/BookDtos.cs:7-11` `[Required(AllowEmptyStrings=false)]`; tested `BooksEndpointsTests.cs:50-63` |
| R10 | GET /health | ✓ implemented | `Controllers/HealthController.cs:9-10` |
| R11 | README with setup/run | ✓ implemented | `README.md` — prereqs, build, run, test, API, examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 11 passing test cases across 2 test classes |
| P1 | BDD Given/When/Then tests (prompt=bdd) | ✓ followed | `Given_..._When_..._Then_...` names + Given/When/Then comments throughout `BooksEndpointsTests.cs`, `HealthEndpointTests.cs` |

## Build & Test

Scores read from `retort.db` / `scores.json` (not re-run per skill guidance):

```text
test_coverage = 0.9787   # build + tests executed; 11/11 passing
defect_rate   = 1.0      # build + test succeeded
code_quality  = 1.0      # lint/quality clean
maintainability = 0.8949
idiomatic     = 0.82
```

Agent log (`_agent_stdout.log`) corroborates: "clean dotnet build/dotnet test (11/11 passing)"
plus a manual end-to-end curl CRUD run. One non-blocking `NU1903` advisory on the transitive
SQLitePCLRaw native package.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, .cs) | 193 |
| Lines of code (tests, .cs) | 239 |
| Files (src + tests, excl. bin/obj) | 14 |
| Dependencies (API PackageReferences) | 2 (1 unused: EFCore.InMemory) |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| Build duration | ~276s (full run wall-clock incl. agent) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] NU1903 advisory on transitive SQLitePCLRaw.lib.e_sqlite3 (no patched version available)
2. [low] Unused `Microsoft.EntityFrameworkCore.InMemory` package reference in `BookApi.csproj:10`
3. [info] No explicit error handling around EF Core `SaveChangesAsync` (relies on framework defaults)

No critical/high/medium findings. All 12 spec requirements and the BDD prompt instruction are
satisfied; tests pass with zero skips.

## Reproduce

```bash
cd experiment-15-sonnet5/rest-api/runs/language=csharp_model=sonnet-5_prompt=bdd/rep1
# Scores (do not re-run toolchain):
cat scores.json
# Build & test locally (requires .NET 10 SDK):
dotnet build BookApi.slnx
dotnet test BookApi.slnx
# Skip / test-count checks:
grep -rE "Skip\s*=|\[Ignore\]" tests --include="*.cs" | wc -l   # 0
grep -rE "\[Fact\]|\[Theory\]" tests --include="*.cs" | wc -l   # 10 (+2 InlineData = 11 cases)
```
