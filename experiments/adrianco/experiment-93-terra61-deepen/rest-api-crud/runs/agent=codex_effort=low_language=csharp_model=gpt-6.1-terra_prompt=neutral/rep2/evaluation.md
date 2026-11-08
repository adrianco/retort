# Evaluation: agent=codex_effort=low_language=csharp_model=gpt-6.1-terra_prompt=neutral · rep 2

## Summary

- **Factors:** language=csharp, model=gpt-6.1-terra, agent=codex, effort=low, prompt=neutral
- **Status:** ok (this was a REPAIR attempt — TASK.md/FEEDBACK.md say the previous attempt failed build/tests)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 4 tests (xUnit integration via WebApplicationFactory), 0 skipped (4 effective); passed per harness scoring (defect_rate=1.0)
- **Build:** pass — from scores.json (defect_rate=1.0); not re-run per skill
- **Lint:** pass — code_quality=0.956
- **Architecture:** summary skill unavailable (single 119-line `Program.cs`: minimal-API routes + `BookStore` SQLite repository)
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 2 info)

Stored scores (`scores.json`): test_coverage=0.75 (line coverage), code_quality=0.956, defect_rate=1.0, maintainability=1.0, idiomatic=0.82, token_efficiency=0.0043.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates (title, author, year, isbn) | ✓ implemented | `Program.cs:13-19`, `BookStore.Create` :81; test `CreateGetUpdateDeleteRoundTrip` |
| R2 | GET /books lists all | ✓ implemented | `Program.cs:10`, `BookStore.List` :59; test `AuthorFilterReturnsMatchingBooks` |
| R3 | ?author= filter | ✓ implemented | `Program.cs:63` parameterised `WHERE author = $author COLLATE NOCASE`; test asserts single match |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `Program.cs:11-12`; round-trip test asserts 404 after delete |
| R5 | PUT /books/{id} updates | ✓ implemented | `Program.cs:20-25`, `BookStore.Update` :91; tests for 200, 400, 404 |
| R6 | DELETE /books/{id} | ✓ implemented | `Program.cs:26-27` (204/404); tested |
| R7 | SQLite persistence | ✓ implemented | `Microsoft.Data.Sqlite` 10.0.13, `books.db` default (`Program.cs:4,55`) |
| R8 | JSON + proper status codes | ✓ implemented | 201+Location, 200, 204, 400 problem+json, 404 (empty body — low finding) |
| R9 | title/author required (400) | ✓ implemented | `Validate` :30-36, whitespace rejected; test `InvalidInputIsRejected…` |
| R10 | GET /health | ✓ implemented | `Program.cs:9` → `{status:"healthy"}`; test `HealthReturnsOk` |
| R11 | README setup/run | ✓ implemented | `README.md` — restore/run/test commands, config, endpoints |
| R12 | ≥3 tests that run | ✓ implemented | 4 `[Fact]`s in `tests/ApiTests.cs`; test_coverage=0.75 > 0 |

Prompt factor `neutral` adds no checkable instructions (no P-requirements).

## Build & Test

```text
Not re-run (skill step 2). scores.json: defect_rate=1.0 ⇒ build + tests passed; test_coverage=0.75.
Agent's own `dotnet test` attempts failed inside the codex sandbox (local sockets blocked), see _agent_stdout.log.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 119 (Program.cs) + 69 (tests) |
| Files (source) | 2 .cs, 2 .csproj, 1 .sln |
| Dependencies | 1 runtime (Microsoft.Data.Sqlite), 4 test |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

1. [low] 404 responses have an empty body rather than a JSON error
2. [low] year and isbn are not validated
3. [info] Agent could not run its own tests in the sandbox; harness ran them fine
4. [info] Line coverage is 75%

## Reproduce

```bash
cd <run_dir>
cat scores.json
dotnet test tests/Books.Tests.csproj
```
