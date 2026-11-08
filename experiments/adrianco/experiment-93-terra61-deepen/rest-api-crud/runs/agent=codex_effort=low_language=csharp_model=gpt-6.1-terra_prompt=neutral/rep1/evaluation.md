# Evaluation: rest-api-crud · agent=codex effort=low language=csharp model=gpt-6.1-terra prompt=neutral · rep 1

## Summary

- **Factors:** language=csharp, model=gpt-6.1-terra, agent=codex, effort=low, prompt=neutral
- **Status:** ok — repair task; build + all tests pass
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective)
- **Build:** pass — from `test_coverage=1.0` in `scores.json`
- **Lint:** pass — from `code_quality=1.0` in `scores.json`
- **Architecture:** run-summary skill unavailable in this session — see module notes below
- **Findings:** 0 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low)

This was a REPAIR task (`TASK.md`): a prior attempt failed because "the build/tests did not
fully pass". The repaired code now builds cleanly and all tests run and pass
(`test_coverage=1.0`, `defect_rate=1.0`, `maintainability=1.0`, `code_quality=1.0`;
`idiomatic=0.55`). Every pinned requirement from `REQUIREMENTS.json` is satisfied with
concrete evidence.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `Program.cs:21-27` MapPost → `BookStore.Create` `Program.cs:98-107` (INSERT…RETURNING) |
| R2 | GET /books lists all books | ✓ implemented | `Program.cs:18` MapGet → `BookStore.List` `Program.cs:78-88` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `Program.cs:18` author param; SQL filter `Program.cs:82` (`author = $author COLLATE NOCASE`); test `tests/ApiTests.cs:42-50` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `Program.cs:19-20` returns Ok/NotFound; `BookStore.Get` `Program.cs:89-97` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `Program.cs:28-33` MapPut → `BookStore.Update` `Program.cs:108-117` (UPDATE…RETURNING, 404 if absent) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `Program.cs:34-35` → `BookStore.Delete` `Program.cs:118-125` (NoContent/NotFound) |
| R7 | Data stored in SQLite | ✓ implemented | `Microsoft.Data.Sqlite` (`Books.csproj`); `BookStore` opens a SqliteConnection and CREATE TABLE `Program.cs:62-68` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `Results.Ok/Created(201)/NotFound(404)/ValidationProblem(400)/NoContent(204)` throughout `Program.cs:17-35` |
| R9 | Input validation: title and author required | ✓ implemented | `Validate` `Program.cs:39-45` → 400 on POST/PUT; test `tests/ApiTests.cs:51-61` |
| R10 | GET /health health check | ✓ implemented | `Program.cs:17` returns `{status:"healthy"}`; test `tests/ApiTests.cs:71-72` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — restore/run/test commands, env var, endpoint docs |
| R12 | At least 3 unit/integration tests | ✓ implemented | 5 `[Fact]` tests in `tests/ApiTests.cs`; `test_coverage=1.0` |

No requirement is partial or missing. No enhancements-beyond-spec worth flagging.

## Build & Test

Build/test were **not re-run** — stored mechanical scores are authoritative (per
evaluate-run skill). From `scores.json`:

```text
test_coverage = 1.0   → build succeeded + all tests passed
code_quality  = 1.0   → lint/quality clean
defect_rate   = 1.0   → build+test succeeded
maintainability = 1.0
idiomatic     = 0.55
token_efficiency = 0.00302
```

Tests (`tests/ApiTests.cs`, xUnit via custom in-process `TestRunner`): 5 Facts —
`CreateGetUpdateAndDeleteBook`, `ListFiltersByAuthor`, `RequiredFieldsAreValidated`,
`DataPersistsAcrossStoreInstances`, `HealthReturnsOk`. 0 skipped/disabled.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, *.cs excl bin/obj) | 228 |
| Files (excl bin/obj/.git) | 17 |
| Dependencies | Microsoft.Data.Sqlite (app); Mvc.Testing, Test.Sdk, xunit, xunit.runner (tests) |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

None. No critical/high/medium/low findings — `findings.jsonl` is empty.

## Reproduce

```bash
cd "experiments/adrianco/experiment-93-terra61-deepen/rest-api-crud/runs/agent=codex_effort=low_language=csharp_model=gpt-6.1-terra_prompt=neutral/rep1"
cat scores.json                                    # stored mechanical scores
cat REQUIREMENTS.json                              # pinned 12-requirement checklist
grep -rnE "Skip\s*=|\[Fact\(Skip" tests/ --include="*.cs" | wc -l   # 0 skips
grep -rcE "\[Fact\]|\[Theory\]" tests/*.cs         # 5 Facts
```
