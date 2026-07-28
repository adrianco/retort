# Evaluation: agent=codex language=go prompt=neutral · rep 1

## Summary

- **Factors:** language=go, agent=codex, model=gpt-5.6-luna, prompt=neutral, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass (`defect_rate=1.0` from scores.json)
- **Lint:** pass — `code_quality=0.956` from scores.json
- **Architecture:** single-package Go net/http service; summary skill unavailable
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:152-162` handleBooks POST → `Store.Create` (main.go:54-61) |
| R2 | GET /books lists all | ✓ implemented | `main.go:163-169` → `Store.List` (main.go:73-94) |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:75-78,164`; tested `TestValidationAndAuthorFilter` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `main.go:183-193`; 404 on `sql.ErrNoRows` (main.go:185-187) |
| R5 | PUT /books/{id} update | ✓ implemented | `main.go:194-208` → `Store.Update` (main.go:96-109); tested |
| R6 | DELETE /books/{id} | ✓ implemented | `main.go:209-219` → 204; tested `TestUpdateDeleteAndHealth` |
| R7 | Data stored in SQLite | ✓ implemented | `modernc.org/sqlite`; `CREATE TABLE books` (main.go:39-45) |
| R8 | JSON responses + status codes | ✓ implemented | `writeJSON`/`writeError` (main.go:240-247); 201/200/204/400/404/405/500 |
| R9 | Validation: title + author required | ✓ implemented | `decodeInput` (main.go:232-235) → 400; tested |
| R10 | GET /health | ✓ implemented | `main.go:131-138` → `{"status":"ok"}`; tested |
| R11 | README with setup/run | ✓ implemented | `README.md` documents `go run .`, env vars, `go test ./...` |
| R12 | ≥3 unit/integration tests | ✓ implemented | 3 `Test*` funcs in `main_test.go`; `test_coverage=0.634` (>0) |

**Prompt factor (neutral):** `prompts/neutral.md` prescribes no methodology and asks for tests demonstrating the requirements — satisfied by the 3 passing httptest-based tests.

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate output):

```text
test_coverage  = 0.634   (tests executed and passed; 63.4% statement coverage)
defect_rate    = 1.0     (build + test succeeded)
code_quality   = 0.9556
maintainability= 0.9005
idiomatic      = 0.78
token_efficiency = 0.0245
```

Skipped-test scan (`grep -rE "t\.Skip\(|t\.Skipf\("`): 0 skips.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 363 (main.go 269 + main_test.go 94) |
| Files | 9 (excl. .git, agent logs, caches) |
| Dependencies (direct) | 1 (`modernc.org/sqlite`; 21 total incl. indirect) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top items (full list in `findings.jsonl`):

1. [low] No test covers the 404 not-found path for GET/PUT/DELETE /books/{id}
2. [low] No test for malformed-JSON (400) / method-not-allowed (405) responses
3. [info] Pure-Go `modernc.org/sqlite` avoids cgo — portable build

No requirement gaps, build failures, test failures, or skipped tests.

## Reproduce

```bash
cd runs/agent=codex_language=go_prompt=neutral/rep1
cat scores.json            # stored mechanical scores (build/test/quality)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # skip count = 0
# Optional full re-run (not required — scores already stored):
# go test ./...
```
