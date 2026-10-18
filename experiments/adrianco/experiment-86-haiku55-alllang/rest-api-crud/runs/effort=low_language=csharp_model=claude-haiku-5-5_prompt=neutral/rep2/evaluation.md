# Evaluation: effort=low_language=csharp_model=claude-haiku-5-5_prompt=neutral · rep 2

## Summary

- **Factors:** language=csharp, model=claude-haiku-5-5, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 13 passed / 0 failed / 0 skipped (13 effective)
- **Build:** pass — `test_coverage=0.9751`, `defect_rate=1.0` from `scores.json` (agent log: `0 Warning(s) 0 Error(s)`)
- **Lint:** pass — `code_quality=1.0` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 0 items in `findings.jsonl`

A clean, complete run. All 12 pinned requirements are implemented, the build is warning-free, and all 13 tests pass with no skips. The solution is cleanly layered (host / records / validator / repository interface + SQLite implementation) and exceeds the spec with ISBN-10/13 validation, year-range and length checks, RFC 7807 error bodies, and a typed `long` route constraint.

## Requirements

Checklist is the pinned `REQUIREMENTS.json` (12 items, constant denominator for every run of this task).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `Program.cs:22` `books.MapPost` → `repo.CreateAsync`; test `Create_then_get_by_id_round_trips_book` |
| R2 | GET /books lists all | ✓ implemented | `Program.cs:32` `books.MapGet("")` → `ListAsync`; test `List_filters_by_author...` (asserts all=2) |
| R3 | GET /books ?author= filter | ✓ implemented | `SqliteBookRepository.cs:ListAsync` `WHERE ... author = $author COLLATE NOCASE`; test asserts filtered=1 |
| R4 | GET /books/{id} single + 404 | ✓ implemented | `Program.cs:35` `MapGet("/{id:long}")` → `NotFoundResult`; test `Unknown_id_returns_404...` |
| R5 | PUT /books/{id} updates | ✓ implemented | `Program.cs:41` `MapPut` → `UpdateAsync`; test `Update_replaces_book_and_delete_removes_it` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `Program.cs:50` `MapDelete` → `DeleteAsync` (204/404); same test |
| R7 | SQLite / embedded DB | ✓ implemented | `SqliteBookRepository.cs` uses `Microsoft.Data.Sqlite`, real `books` table |
| R8 | JSON + correct status codes | ✓ implemented | `Results.Created/Ok/NoContent/NotFound/ValidationProblem`; tests assert 201/200/204/404/400 |
| R9 | Validation: title & author required | ✓ implemented | `BookValidator.cs:Validate` rejects blank title/author; test `Create_without_title_or_author_returns_400` |
| R10 | GET /health | ✓ implemented | `Program.cs:18` `app.MapGet("/health", ...)`; test `Health_returns_ok` |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, run, test, endpoints, examples |
| R12 | ≥ 3 tests | ✓ implemented | 9 test methods / 13 effective cases; `test_coverage=0.9751 > 0` |

## Build & Test

```text
dotnet build BookApi.slnx
    0 Warning(s)
    0 Error(s)
```

```text
dotnet test BookApi.slnx
Passed!  - Failed: 0, Passed: 13, Skipped: 0, Total: 13, Duration: 411 ms - BookApi.Tests.dll (net10.0)
```

(Scores read from `scores.json` per the evaluate-run skill — not re-run: `test_coverage=0.9751`, `code_quality=1.0`, `defect_rate=1.0`, `maintainability=0.926`, `idiomatic=0.62`.)

## Metrics

| Metric | Value |
|--------|-------|
| Source files (src+tests, no obj/bin) | 10 |
| Source modules | 5 |
| Test files | 2 |
| Tests total | 13 |
| Tests effective | 13 |
| Skip ratio | 0% |
| test_coverage | 0.9751 |
| code_quality | 1.0 |
| maintainability | 0.926 |
| idiomatic | 0.62 |
| token_efficiency | 0.027 |
| Agent cost | $0.0143 |

## Findings

None. No build failures, no test failures, no skipped tests, no missing or partial requirements. `findings.jsonl` is empty.

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=csharp_model=claude-haiku-5-5_prompt=neutral/rep2"
cat scores.json                                    # stored mechanical scores (do not re-run build/test)
cat ../../REQUIREMENTS.json                         # pinned 12-item checklist
grep -rE "Skip|\[Ignore\]" tests --include="*.cs"  # skip check (none)
# optional rebuild: dotnet test BookApi.slnx
```
