# Evaluation: csharp · codex · gpt-5.6-terra · rep 1

## Summary

- **Factors:** language=csharp, agent=codex, model=gpt-5.6-terra, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — from `defect_rate=1.0`
- **Build:** pass (`defect_rate=1.0` from scores.json; agent log item_13 "Build succeeded. 0 Error(s)")
- **Lint:** pass — `code_quality=1.0`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

Scores (from `scores.json`): test_coverage=0.6616, code_quality=1.0, defect_rate=1.0, maintainability=0.5985, idiomatic=0.74, token_efficiency=0.0112.

Note: the agent's own `dotnet test` was aborted by the sandbox's loopback-socket restriction (`SocketException: Permission denied` from the vstest runner, log item_11/12), but the build succeeded and retort's scorer ran the tests successfully afterward — `defect_rate=1.0` confirms build+test passed and `test_coverage=0.6616` is the resulting line coverage.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `Program.cs:21` MapPost → `BookRepository.CreateAsync` (INSERT) |
| R2 | GET /books lists all | ✓ implemented | `Program.cs:31` MapGet → `GetAllAsync` |
| R3 | GET /books ?author= filter | ✓ implemented | `BookRepository.cs` `GetAllAsync` `WHERE Author LIKE $author`; test `GetAll_WithAuthorFilter_ReturnsMatchingBooksOnly` |
| R4 | GET /books/{id} by id | ✓ implemented | `Program.cs:34` MapGet `/books/{id:int}`, 404 via `Results.NotFound()` (line 37) |
| R5 | PUT /books/{id} updates | ✓ implemented | `Program.cs:40` MapPut → `UpdateAsync`; test `Update_ReplacesBookAndReturnsUpdatedValue` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `Program.cs:50` MapDelete → `DeleteAsync`; test `Delete_RemovesBookAndReportsMissingId` |
| R7 | Data stored in SQLite | ✓ implemented | `Microsoft.Data.Sqlite` (csproj), `BookRepository` CREATE TABLE / SQL persistence |
| R8 | JSON + correct status codes | ✓ implemented | `Results.Created`(201)/`Ok`(200)/`NotFound`(404)/`NoContent`(204)/`ValidationProblem`(400) in `Program.cs` |
| R9 | Validation: title+author required | ✓ implemented | `Program.cs:55` `Validate()` rejects blank title/author → 400 (applied on POST and PUT) |
| R10 | GET /health | ✓ implemented | `Program.cs:19` `MapGet("/health", … status = "healthy")` |
| R11 | README with setup/run | ✓ implemented | `README.md` — Run/Endpoints/Test sections, `dotnet run`/`dotnet test` |
| R12 | ≥3 unit/integration tests | ✓ implemented | 4 `[Fact]` tests in `BookRepositoryTests.cs`, 0 skipped; `defect_rate=1.0` |

## Build & Test

Not re-run — scores read from `scores.json` (inline gate) per the evaluate-run skill.

```text
# build (agent log item_13)
dotnet build BookCollection.slnx --no-restore -m:1 /nodeReuse:false -v:minimal
  Build succeeded.  2 Warning(s) (NU1900 offline nuget)  0 Error(s)
```

```text
# tests: scorer result
defect_rate = 1.0   -> build + all tests passed
test_coverage = 0.6616  (line coverage)
4 [Fact] tests, 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (.cs, source+tests, excl. bin/obj) | 245 |
| Files (excl. bin/obj/.git) | 18 |
| Dependencies | API 1 (Microsoft.Data.Sqlite); Tests 4 (xunit, test-sdk, runner, coverlet) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build | pass |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Tests exercise only the repository layer, not HTTP endpoints — `BookRepositoryTests.cs` calls `BookRepository` directly; routing/validation/`/health` uncovered.
2. [info] Line coverage 0.66 — `Validate()` and the `/health` handler are not reached by any test.
3. [info] PUT is full-replace and returns 404 for unknown id (`Program.cs:47`) — conforms to spec, noted for comparison.

No critical/high/medium findings: all 12 pinned requirements are implemented, the build passes, and 4 tests pass with no skips.

## Reproduce

```bash
cd "experiments/adrianco/experiment-56-terra-alllang/bookshop/runs/agent=codex_effort=default_language=csharp_model=gpt-5.6-terra_prompt=neutral/rep1"
cat scores.json                       # stored mechanical scores (no re-run)
dotnet build BookCollection.slnx      # Build succeeded, 0 errors
dotnet test  BookCollection.slnx      # 4 tests pass (needs loopback socket; blocked in sandbox)
```
