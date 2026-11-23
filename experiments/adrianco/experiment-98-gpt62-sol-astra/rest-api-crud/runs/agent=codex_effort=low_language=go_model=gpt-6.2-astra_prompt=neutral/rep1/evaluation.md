# Evaluation: rest-api-crud · agent=codex effort=low language=go model=gpt-6.2-astra prompt=neutral · rep 1

## Summary

- **Factors:** language=go, model=gpt-6.2-astra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective) — `test_coverage=0.785`, `defect_rate=1.0` from `scores.json`
- **Build:** pass (not re-run; `defect_rate=1.0` ⇒ build + tests succeeded)
- **Lint:** pass — `code_quality=0.9556` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:149 api.save` (id=0) INSERT; `TestLifecycle` POST→201 |
| R2 | GET /books lists all books | ✓ implemented | `main.go:122 api.list`; `TestFilteringAndPersistence` ""→2 |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:125-128` WHERE author=?; test `?author=A+B`→1 |
| R4 | GET /books/{id} single book | ✓ implemented | `main.go:85-90` SELECT by id, 404 if absent; `TestLifecycle` GET→200 |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.go:166-170` UPDATE ... RETURNING; `TestLifecycle` PUT→200 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.go:93-98` DELETE ... RETURNING, 204; test DELETE→204, re-DELETE→404 |
| R7 | Data stored in SQLite | ✓ implemented | `main.go:16,30-42` mattn/go-sqlite3 `openDB`; persistence re-open test |
| R8 | JSON responses + status codes | ✓ implemented | `main.go:44-51 respond/problem`; 201/200/204/400/404/405/500 covered |
| R9 | Validation: title & author required | ✓ implemented | `main.go:157-162` trim + reject blank→400; `TestValidationAndHealth` |
| R10 | GET /health | ✓ implemented | `main.go:59-68` 200 ok / 503 on ping failure; test /health→200 |
| R11 | README with setup/run | ✓ implemented | `README.md` — build/run/curl, flags, route table |
| R12 | ≥3 unit/integration tests | ✓ implemented | 3 test funcs; `test_coverage=0.785>0`, `defect_rate=1.0` |

## Build & Test

Build and tests were **not re-run** — stored mechanical scores are authoritative (per evaluate-run):

```text
scores.json: {"code_quality":0.9556,"token_efficiency":0.0331,"test_coverage":0.785,
              "defect_rate":1.0,"maintainability":0.8740,"idiomatic":0.62}
defect_rate=1.0  => `go test ./...` built and passed
test_coverage=0.785 => 78.5% statement coverage, all tests green
```

Tests (`main_test.go`): `TestLifecycle`, `TestFilteringAndPersistence`, `TestValidationAndHealth` — httptest against the real handler over in-memory and temp-file SQLite. No `t.Skip` calls.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 270 (main.go 192 + main_test.go 78) |
| Files | 12 (incl. logs/meta); 2 Go source |
| Dependencies | 1 direct (`mattn/go-sqlite3`); go.sum 2 lines |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | not re-run (gate scores used) |

## Findings

Top items (full list in `findings.jsonl`) — all info-level enhancements, no defects:

1. [info] Health check reports DB reachability (503 when down) — `main.go:62`
2. [info] Strict request-body parsing rejects unknown/trailing JSON — `main.go:152-153`
3. [info] 405 responses set accurate `Allow` header — `main.go:113-119`

## Reproduce

```bash
cd "experiments/adrianco/experiment-98-gpt62-sol-astra/rest-api-crud/runs/agent=codex_effort=low_language=go_model=gpt-6.2-astra_prompt=neutral/rep1"
cat scores.json            # mechanical gate scores (authoritative; do not re-run build/test)
grep -rnE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
grep -rnE "^func Test" main_test.go                           # 3 tests
# Optional (not required — gate already scored): go test ./...
```
