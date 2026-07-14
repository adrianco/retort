# Evaluation: language=csharp_model=sonnet-5_prompt=none · rep 1

## Summary

- **Factors:** language=csharp, model=sonnet-5, prompt=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective)
- **Build:** pass — from `defect_rate=1.0` in scores.json (build + tests succeeded)
- **Lint:** pass — `code_quality=1.0` in scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `Program.cs:28-48` maps BookRequest→Book, SaveChangesAsync, 201+Location |
| R2 | GET /books lists all | ✓ implemented | `Program.cs:50-61` returns `db.Books.ToListAsync()` |
| R3 | GET /books ?author= filter | ✓ implemented | `Program.cs:54-57` `Where(b => b.Author.Contains(author))`; test `BooksApiTests.cs:54` |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `Program.cs:63-67` FindAsync → 404/200; test `BooksApiTests.cs:72` |
| R5 | PUT /books/{id} updates | ✓ implemented | `Program.cs:69-91` updates fields; test `BooksApiTests.cs:82` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `Program.cs:93-105` Remove→204; test `BooksApiTests.cs:100` |
| R7 | SQLite / embedded DB persistence | ✓ implemented | `Program.cs:11` UseSqlite; `Data/BookDbContext.cs`; `EnsureCreated()` at `Program.cs:18` |
| R8 | JSON responses + correct status codes | ✓ implemented | 201/200/204/400/404 across `Program.cs:26-105`; Results.* helpers |
| R9 | Validation: title & author required | ✓ implemented | `Models/BookDtos.cs:7,10` [Required(AllowEmptyStrings=false)]; test `BooksApiTests.cs:41` |
| R10 | GET /health | ✓ implemented | `Program.cs:26` returns `{status:"healthy"}`; test `BooksApiTests.cs:10` |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, run, test, full API reference |
| R12 | ≥3 unit/integration tests | ✓ implemented | 7 `[Fact]` in `BooksApiTests.cs`; `test_coverage=0.2264 > 0` |

## Build & Test

Scores read from `scores.json` (skill Step 2 — no re-run):

```text
code_quality      = 1.0        # lint/quality clean
defect_rate       = 1.0        # build + tests succeeded
test_coverage     = 0.2264     # line coverage (tests ran and passed)
maintainability   = 0.614
idiomatic         = 0.78
token_efficiency  = 0.0028
```

Agent's own verification (`_agent_stdout.log`): "`dotnet build` (0 warnings/errors), `dotnet test` (7/7 passing)". `test_coverage` here is a coverage fraction, not the pass-rate gate; `defect_rate=1.0` confirms build+tests passed.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source .cs, excl obj/bin) | 322 |
| Files (source+test, excl obj/bin) | 12 |
| Dependencies (PackageReference, unique) | 8 |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |
| Build duration | not separately timed (defect_rate=1.0) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] README claims case-insensitive author filter, but code uses `Contains` whose case sensitivity is implicit in SQLite's LIKE/instr translation (`README.md:101` vs `Program.cs:56`)
2. [info] Clean DTO/entity separation with validation shared by POST+PUT (`Models/BookDtos.cs`, `Program.cs:30,71`)
3. [info] Integration tests isolate DB via in-memory SQLite per factory (`ApiFactory.cs:12-30`)

No critical, high, or medium findings. This is a clean, spec-complete run.

## Reproduce

```bash
cd experiment-15-sonnet5/rest-api/runs/language=csharp_model=sonnet-5_prompt=none/rep1
cat scores.json                      # stored build/test/lint scores (do not re-run)
dotnet build                         # optional: 0 warnings/errors
dotnet test                          # optional: 7/7 passing
```
