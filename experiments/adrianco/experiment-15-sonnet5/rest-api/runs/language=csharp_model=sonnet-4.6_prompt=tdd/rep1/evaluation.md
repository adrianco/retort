# Evaluation: language=csharp_model=sonnet-4.6_prompt=tdd · rep 1

## Summary

- **Factors:** language=csharp, model=sonnet-4.6, prompt=tdd (framework=ASP.NET Core 10)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (+ TDD prompt P1–P4 satisfied)
- **Tests:** 10 passed / 0 failed / 0 skipped (10 effective)
- **Build:** pass — from `defect_rate=1.0` in scores.json (not re-run)
- **Lint:** pass — `code_quality=1.0` in scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 2 low, 2 info)

Clean run. All 12 pinned requirements implemented, comprehensive integration
test suite (10 tests) passing, idiomatic C# with EF Core + SQLite. No skipped or
disabled tests. Mechanical scores read from `scores.json` (build/test/lint not
re-run, per skill).

## Requirements

Checklist is the pinned `REQUIREMENTS.json` (R1–R12); `tdd` prompt adds P1–P4.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `Controllers/BooksController.cs:33-47` `Create`, returns 201 + Location |
| R2 | GET /books lists all | ✓ implemented | `BooksController.cs:12-23` `GetAll` |
| R3 | GET /books ?author= filter | ✓ implemented | `BooksController.cs:16-17` `Where(b => b.Author == author)` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `BooksController.cs:25-31` `GetById`, `NotFound()` when null |
| R5 | PUT /books/{id} updates | ✓ implemented | `BooksController.cs:49-62` `Update` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `BooksController.cs:64-72` `Delete`, 204 |
| R7 | Data stored in SQLite | ✓ implemented | `Program.cs:6-7` `UseSqlite`; `Data/BookDbContext.cs` EF Core |
| R8 | JSON + appropriate status codes | ✓ implemented | `Ok`/`CreatedAtAction`/`NotFound`/`NoContent`/`BadRequest` throughout |
| R9 | Validation: title & author required | ✓ implemented | `Models/BookDtos.cs:6-11` `[Required]` + `[ApiController]` → 400; tests `PostBook_MissingTitle/Author_Returns400` |
| R10 | GET /health | ✓ implemented | `Program.cs:19` returns `{status:"healthy"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — prerequisites, `dotnet run`, `dotnet test`, curl examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | `BooksApiTests.cs` — 10 `[Fact]` tests; `test_coverage=0.9857` |
| P1 | Write failing test before impl | ✓ implemented | `_agent_stdout.log`: tests written first against non-existent API (see F/P1 caveat) |
| P2 | Minimum code to pass each test | ✓ implemented | Lean controllers/DTOs, no gold-plating; 304 SLOC total |
| P3 | Refactor after green | ✓ implemented | Idiomatic final form (primary constructors, records); consistent structure |
| P4 | Tight red/green/refactor cycle | ✓ implemented | 32 turns, test-first per agent log; process ordering not statically verifiable |

## Build & Test

Not re-run (per skill §2 — mechanical scores already computed). Read from
`scores.json`:

```text
scores.json: {"code_quality": 1.0, "test_coverage": 0.9857, "defect_rate": 1.0,
              "maintainability": 0.5726, "idiomatic": 0.82, "token_efficiency": 0.0064}
```

```text
_agent_stdout.log: "All 10 tests pass."
dotnet test → 10 [Fact] tests, 0 skipped (grep for Skip=/[Ignore]/Fact(Skip → 0)
```

- `defect_rate=1.0` ⇒ build + tests succeeded.
- `test_coverage=0.9857` ⇒ tests executed (non-zero) with near-complete coverage.
- `code_quality=1.0` ⇒ lint/quality gate clean.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (C# source only) | 304 |
| Files (non-build) | 12 |
| Dependencies (PackageReferences) | 8 (2 API, 6 test) |
| Tests total | 10 |
| Tests effective | 10 |
| Skip ratio | 0% |
| code_quality | 1.00 |
| maintainability | 0.57 |
| idiomatic | 0.82 |
| Build duration | not re-run (scores cached) |

## Findings

All 4 findings are low/info — no requirement gaps, no test failures, no skips.
Full list in `findings.jsonl`:

1. [info] P1 — TDD process consistent with artifacts but not statically verifiable
2. [low] F1 — PUT uses full-replace semantics (omitted optional fields nulled)
3. [low] F2 — `?author=` filter is exact-match only (meets spec)
4. [info] F3 — `/health` does not probe DB connectivity

## Reproduce

```bash
cd experiment-15-sonnet5/rest-api/runs/language=csharp_model=sonnet-4.6_prompt=tdd/rep1
cat scores.json                       # cached mechanical scores (build/test/lint)
cat _agent_stdout.log                 # agent result: "All 10 tests pass."
grep -rcE "\[Fact\]" BookCollection.Tests   # 10 tests
grep -rniE "Skip *=|\[Ignore\]|Fact\(Skip" --include="*.cs" .   # 0 skips
# Optional full re-run (not required — scores already computed):
# dotnet test
```
