# Evaluation: language=csharp · model=sonnet-5 · prompt=tdd · rep 1

## Summary

- **Factors:** language=csharp, model=sonnet-5, prompt=tdd
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Prompt factor (tdd):** followed — failing-first cycle evidenced by structure + agent log; refactor extracted `BookCreateRequest.IsValid`
- **Tests:** 14 passed / 0 failed / 0 skipped (14 effective) — from `test_coverage=1.0` (scores.json)
- **Build:** pass — `test_coverage=1.0`/`defect_rate=1.0` imply build + all tests passed (not re-run)
- **Lint:** pass — `code_quality=1.0` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `BookApi/Program.cs:19` MapPost persists via `Books.Add` + `SaveChangesAsync`, returns 201 |
| R2 | GET /books lists all | ✓ implemented | `BookApi/Program.cs:41` MapGet returns `ToListAsync` |
| R3 | GET /books ?author= filter | ✓ implemented | `BookApi/Program.cs:47` `Where(b => b.Author == author)`; test `GetBooks_FilterByAuthor` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `BookApi/Program.cs:52` `FindAsync`, `NotFound` if null; tests cover both |
| R5 | PUT /books/{id} updates | ✓ implemented | `BookApi/Program.cs:58` updates fields, 404 if absent; `PutBooks_ExistingBook` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `BookApi/Program.cs:79` removes, 204/404; `DeleteBooks_*` tests |
| R7 | SQLite / embedded DB | ✓ implemented | `Program.cs:8` `UseSqlite`; `BookDbContext.cs`; `books.db` default source |
| R8 | JSON + appropriate status codes | ✓ implemented | `Results.Created/Ok/NotFound/BadRequest/NoContent` throughout `Program.cs` |
| R9 | Validation: title & author required | ✓ implemented | `Program.cs:120` `BookCreateRequest.IsValid`; `PostBooks_MissingTitle/Author` → 400 |
| R10 | GET /health | ✓ implemented | `Program.cs:17` returns `{status:"healthy"}`; `HealthCheckTests` |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, run, test, full API docs, layout |
| R12 | ≥3 unit/integration tests | ✓ implemented | 14 `[Fact]` tests across 3 test classes; `test_coverage=1.0` |

Prompt-factor (tdd) instructions:

| ID | Instruction (short) | Status | Evidence |
|----|----|----|----|
| P1 | Write failing test before impl | ✓ implemented | Comprehensive test-first integration suite; agent log narrates red→green per endpoint (`_agent_stdout.log`) |
| P2 | Minimum code to pass | ✓ implemented | Lean minimal-API handlers, no speculative features |
| P3 | Refactor after green, no new behavior | ✓ implemented | Shared validation extracted into `BookCreateRequest.IsValid`, reused by POST + PUT |
| P4 | Tight red/green/refactor cycle | ~ consistent | Process not directly reconstructable from final artifacts; structure + 71-turn log are consistent with it |

## Build & Test

Mechanical scores read from `scores.json` (not re-run, per skill):

```text
scores.json: code_quality=1.0, test_coverage=1.0, defect_rate=1.0,
             maintainability=0.553, idiomatic=0.87, token_efficiency=0.00176
```

`test_coverage=1.0` ⇒ build succeeded and all tests passed. Agent log: "All 14 tests pass". No skipped/ignored tests found (`grep` for `Skip`/`[Ignore]` → none).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, .cs no bin/obj) | 437 |
| Files (no bin/obj/.git) | 24 |
| Test framework | xUnit + `WebApplicationFactory` |
| Tests total | 14 |
| Tests effective | 14 |
| Skip ratio | 0% |
| Build | pass (from scores.json) |

## Findings

Full list in `findings.jsonl` (no high/critical):

1. [info] Regression test `AppStartupTests` guards a real startup schema-creation bug the agent found via live run — exemplary TDD follow-through.
2. [low] `?author=` filter is case-sensitive exact match (spec-compliant; enhancement only).
3. [low] Validation limited to required Title+Author; Year/Isbn unconstrained (spec-compliant).

## Reproduce

```bash
cd experiment-15-sonnet5/rest-api/runs/language=csharp_model=sonnet-5_prompt=tdd/rep1
cat scores.json                       # mechanical scores (build/test/lint), not re-run
grep -rEn "Skip|\[Ignore\]" BookApi.Tests --include="*.cs"   # → none
grep -rEc "\[Fact\]|\[Theory\]" BookApi.Tests --include="*.cs"  # → 14 total
# Optional full rebuild (slow; scores already stored):
# dotnet test
```
