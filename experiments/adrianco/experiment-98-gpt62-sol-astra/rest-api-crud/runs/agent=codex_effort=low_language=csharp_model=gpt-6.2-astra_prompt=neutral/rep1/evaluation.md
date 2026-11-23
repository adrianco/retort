# Evaluation: agent=codex_effort=low_language=csharp_model=gpt-6.2-astra_prompt=neutral · rep 1

## Summary

- **Factors:** language=csharp, model=gpt-6.2-astra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective) — `test_coverage=1.0`
- **Build:** pass — from `scores.json` (`test_coverage=1.0` ⇒ build + all tests ran)
- **Lint:** pass — `code_quality=1.0` from `scores.json`
- **Architecture:** ASP.NET Core Web API (net10.0) + EF Core SQLite; see note below
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

Scores read from `scores.json` (inline gate; not re-run): `code_quality=1.0`,
`test_coverage=1.0`, `defect_rate=1.0`, `maintainability=0.624`, `idiomatic=0.82`,
`token_efficiency=0.0057`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates (title, author, year, isbn) | ✓ implemented | `BooksController.cs:48` `Create` → `CreatedAtAction` (201) |
| R2 | GET /books lists all | ✓ implemented | `BooksController.cs:35` `List` returns ordered collection |
| R3 | GET /books ?author= filter | ✓ implemented | `BooksController.cs:38-39` filters by author query param (exact) |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `BooksController.cs:44-45` `Get` → `Ok`/`NotFound` |
| R5 | PUT /books/{id} updates | ✓ implemented | `BooksController.cs:57-65` `Update` → `Ok`/`NotFound` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `BooksController.cs:68-71` `ExecuteDeleteAsync` → `NoContent`/`NotFound` |
| R7 | SQLite / embedded DB | ✓ implemented | `Program.cs:11` `UseSqlite`; `Program.cs:16` `EnsureCreated` |
| R8 | JSON responses + HTTP codes | ✓ implemented | 201/200/404/204 above; `AddProblemDetails` + `[ApiController]` → 400 JSON |
| R9 | Validation: title & author required | ✓ implemented | `BooksController.cs:5` `[Required]` on Title/Author (RequiredAttribute trims → rejects whitespace); test `InvalidFieldsAreRejected` passes |
| R10 | GET /health | ✓ implemented | `Program.cs:20` `MapGet("/health", () => new { status = "ok" })` |
| R11 | README with setup/run | ✓ implemented | `README.md` — SDK install, restore/run, curl example, test command |
| R12 | ≥ 3 tests | ✓ implemented | `BookTests.cs` — 3 `[Fact]` + 1 `[Theory]`(2) = 5 cases; `test_coverage=1.0` |

## Build & Test

Not re-run — stored scores used per skill policy (inline gate `scores.json`):

```text
test_coverage = 1.0   # build succeeded AND all tests executed and passed
code_quality  = 1.0   # lint/quality clean
defect_rate   = 1.0   # build + test succeeded
```

Test suite (`tests/Tests.csproj` compiling `../BookTests.cs`, xunit + Microsoft.AspNetCore.TestHost):
`HealthReportsOk`, `BookCanBeCreatedReplacedAndDeleted`, `InvalidFieldsAreRejected` (Theory ×2),
`ListCanFilterByAuthor`. Each spins the real request pipeline against a per-test temp SQLite DB.
No `Skip`/`[Ignore]` found.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, .cs) | 170 |
| Files (excl. bin/obj/.git) | 14 |
| Dependencies (app) | 1 (`Microsoft.EntityFrameworkCore.Sqlite`) |
| Tests total | 5 effective cases (4 methods) |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Full list in `findings.jsonl`. No correctness, build, test, or requirement issues.

1. [info] Compact but adequate test suite — 5 effective cases cover health, CRUD lifecycle, validation, filtering.
2. [info] Author filter is exact/case-sensitive — satisfies R3; case-insensitive would be an enhancement, not a defect.

## Architecture

Minimal, idiomatic ASP.NET Core Web API on net10.0. `Program.cs` builds the host
(`BookService.Build`, factored out for testability so the integration tests can host it with
`TestServer`), wires EF Core SQLite, ProblemDetails, controllers, and the `/health` minimal-API
endpoint. `BooksController.cs` holds the `Book` entity, `BookInput` record (DataAnnotations
validation), the `BookDb` `DbContext`, and the five CRUD actions. Clean separation; no
dead code. (`run-summary` skill not invoked — codebase is 3 source files / 170 LOC;
structure is captured inline above.)

## Reproduce

```bash
cd "experiments/adrianco/experiment-98-gpt62-sol-astra/rest-api-crud/runs/agent=codex_effort=low_language=csharp_model=gpt-6.2-astra_prompt=neutral/rep1"
cat scores.json                      # stored mechanical scores (not re-run)
cat ../../../REQUIREMENTS.json       # pinned 12-item checklist
grep -rEn "\[Fact\]|\[Theory\]" BookTests.cs
# Optional full run: dotnet test tests/Tests.csproj
```
