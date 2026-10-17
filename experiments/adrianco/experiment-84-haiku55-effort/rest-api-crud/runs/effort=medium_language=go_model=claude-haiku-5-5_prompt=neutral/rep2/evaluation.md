# Evaluation: effort=medium_language=go_model=claude-haiku-5-5_prompt=neutral · rep 2

## Summary

- **Factors:** language=go, model=claude-haiku-5-5, effort=medium, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 15 test functions passed / 0 failed / 0 skipped (15 effective); `test_coverage=0.762` from scores.json
- **Build:** pass — `test_coverage=0.762`, `defect_rate=1.0` (scores.json; not re-run)
- **Lint:** pass — `code_quality=1.0` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `handlers.go:26,42 handleCreate` → `store.go:62 Create`; `handlers_test.go:71` 201 |
| R2 | GET /books lists all | ✓ implemented | `handlers.go:56 handleList` → `store.go:94 List`; `handlers_test.go:127` len 3 |
| R3 | GET /books ?author= filter | ✓ implemented | `store.go:97 WHERE author = ? COLLATE NOCASE`; `handlers_test.go:134` len 2 |
| R4 | GET /books/{id} single + 404 | ✓ implemented | `handlers.go:65 handleGet`; `handlers_test.go:226` 404 missing |
| R5 | PUT /books/{id} updates | ✓ implemented | `handlers.go:78 handleUpdate` → `store.go:125 Update`; `handlers_test.go:93` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `handlers.go:95 handleDelete` → `store.go:145 Delete`; `handlers_test.go:104` 204 |
| R7 | Data stored in SQLite | ✓ implemented | `store.go:9 modernc.org/sqlite`, `store.go:18 schema`; `store_test.go:9` persists across reopen |
| R8 | JSON responses + proper codes | ✓ implemented | `handlers.go:173 writeJSON`; 201/200/204/400/404/409/422/503 across handlers |
| R9 | Validation: title/author required | ✓ implemented | `book.go:43 Validate`; `handlers.go:147`; `handlers_test.go:160` rejects (422, see finding) |
| R10 | GET /health | ✓ implemented | `handlers.go:34 handleHealth` (pings DB); `handlers_test.go:56` 200 {status:ok} |
| R11 | README with setup/run | ✓ implemented | `README.md` — Requirements/Setup/Run/endpoints documented |
| R12 | ≥3 tests | ✓ implemented | 15 test functions across 3 files; `test_coverage=0.762 > 0` |

## Build & Test

Not re-run (per skill step 2 — scores already computed and present in `scores.json`):

```text
scores.json: test_coverage=0.762, code_quality=1.0, defect_rate=1.0,
             maintainability=0.894, idiomatic=0.92, token_efficiency=0.0636
```

`test_coverage=0.762` and `defect_rate=1.0` ⇒ build succeeded and all tests passed.
`grep t.Skip` over `*.go` → 0 skipped tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 489 (book/store/handlers/main.go) |
| Lines of code (tests) | 404 |
| Source files | 4 (+3 test files) |
| Dependencies | 1 direct (`modernc.org/sqlite`), 9 indirect; go.sum 50 lines |
| Tests total | 15 functions |
| Tests effective | 15 |
| Skip ratio | 0% |
| Build/test | pass (scores.json, not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] R9 — validation failures return 422 rather than the 400 hinted in REQUIREMENTS.json (422 is a valid REST choice; not a defect).
2. [info] enhancement — production hardening beyond spec: graceful shutdown, 1 MiB body cap, DisallowUnknownFields, ISBN uniqueness (409), Location header.

No critical/high/medium/low findings. Clean run.

## Reproduce

```bash
cd "experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=medium_language=go_model=claude-haiku-5-5_prompt=neutral/rep2"
cat scores.json                                  # stored build/test/lint scores (not re-run)
grep -rnE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
wc -l book.go store.go handlers.go main.go        # source LOC
# optional, to re-verify: go test ./...
```
